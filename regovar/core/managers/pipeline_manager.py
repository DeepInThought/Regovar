#!env/python3
# coding: utf-8
import ipdb

import os
import shutil
import json
import tarfile
import zipfile
import datetime
import time
import uuid
import subprocess
import requests



from config import *
from core.framework.common import *
from core.framework.postgresql import execute
from core.model import *





# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# PIPELINE MANAGER
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
class PipelineManager:
    def __init__(self):
        pass


    def list(self):
        """
            List all pipelines with minimum of data
        """
        sql = "SELECT id, name, type, status, description, version, image_file_id, starred, installation_date, manifest, documents FROM pipeline ORDER BY id"
        result = []
        for res in execute(sql): 
            result.append({
                "id": res.id,
                "name": res.name,
                "description": res.description,
                "type": res.type,
                "status": res.status,
                "version": res.version,
                "image_file_id": res.image_file_id,
                "starred": res.starred,
                "installation_date": res.installation_date.isoformat(),
                "manifest": res.manifest,
                "documents": res.documents
            })
        return result

    def get(self, fields=None, query=None, order=None, offset=None, limit=None, depth=0):
        """
            Generic method to get pipelines according provided filtering options
        """
        if not isinstance(fields, dict):
            fields = None
        if query is None:
            query = {}
        if order is None:
            order = "name, installation_date desc"
        if offset is None:
            offset = 0
        if limit is None:
            limit = RANGE_MAX
        pipes = Session().query(Pipeline).filter_by(**query).order_by(order).limit(limit).offset(offset).all()
        for p in pipes: p.init(depth)
        return pipes



    def install_init (self, name, metadata={}):
        pipe = Pipeline.new()
        pipe.name = name
        pipe.status = "initializing"
        pipe.save()

        if metadata and len(metadata) > 0:
            pipe.load(metadata)
        log('core.PipeManager.register : New pipe registered with the id {}'.format(pipe.id))
        return pipe



    def install_init_image_upload(self, filepath, file_size, pipe_metadata={}):
        """ 
            Initialise a pipeline installation. 
            To use if the image have to be uploaded on the server.
            Create an entry for the pipeline and the file (image that will be uploaded) in the database.
            Return the Pipeline and the File objects created

            This method shall be used to init a resumable upload of a pipeline 
            (the pipeline/image are not yet installed and available, but we need to manipulate them)
        """
        from core.core import core

        pfile = core.files.upload_init(filepath, file_size)
        pipe = self.install_init(filepath, pipe_metadata)
        pipe.image_file_id = pfile.id
        pipe.save()
        return pipe, pfile



    async def install_init_image_url(self, url, pipe_metadata={}):
        """ 
            Initialise a pipeline installation. 
            To use if the image have to be retrieved via an url.
            Create an entry for the pipeline and the file (image) in the database.
            Async method as the download start immediatly, followed by the installation when it's done

            Return the Pipeline object ready to be used
        """
        raise NotImplementedError("TODO")



    def install_init_image_local(self, filepath, move=False, pipe_metadata={}):
        """ 
            Initialise a pipeline installation. 
            To use if the image have to be retrieved on the local server.
            Create an entry for the pipeline and the file (image) in the database.
            Copy the local file into dedicated Pirus directory and start the installation of the Pipeline

            Return the Pipeline object ready to be used
        """
        from core.core import core

        pfile = core.files.from_local(filepath, move)
        pipe = self.install_init(os.path.basename(filepath), pipe_metadata)

        # Sometime getting sqlalchemy error 'is not bound to a Session' 
        # why it occure here ... why sometime :/ 
        check_session(pfile)
        check_session(pipe)

        pipe.image_file_id = pfile.id
        pipe.save()
        return pipe




    def install(self, pipeline_id, asynch=True):
        """
            Start the installation of the pipeline. (done in another thread)
            The initialization shall be done (image ready to be used)
        """
        from core.core import core

        pipeline = Pipeline.from_id(pipeline_id, 1)
        if not pipeline : 
            raise RegovarException("Pipeline not found (id={}).".format(pipeline_id))
        if pipeline.status != "initializing":
            raise RegovarException("Pipeline status ({}) is not \"initializing\". Cannot perform another installation.".format(pipeline.status))
        if pipeline.image_file and pipeline.image_file.status not in ["uploading", "uploaded", "checked"]:
            raise RegovarException("Wrong pipeline image (status={}).".format(pipeline.image_file.status))

        #if not pipeline.type: pipeline.type = pipeline_type
        #if not pipeline.type :
            #raise RegovarException("Pipeline type not set. Unable to know which kind of installation shall be performed.")
        #if pipeline.type not in core.container_managers.keys():
            #raise RegovarException("Unknow pipeline's type ({}). Installation cannot be performed.".format(pipeline.type))
        #if core.container_managers[pipeline.type].need_image_file and not pipeline.image_file:
            #raise RegovarException("This kind of pipeline need a valid image file to be uploaded on the server.")

        if not pipeline.image_file or pipeline.image_file.status in ["uploaded", "checked"]:
            if asynch:
                run_async(self.__install, pipeline)
            else:
                self.__install(pipeline)



    def __install(self, pipeline):
        from core.core import core
        # Dezip pirus package in the pirus pipeline directory
        root_path = os.path.join(PIPELINES_DIR, str(pipeline.id))
        log('Installation of the pipeline package : ' + root_path)
        os.makedirs(root_path)
        os.chmod(pipeline.image_file.path, 0o777)
        with zipfile.ZipFile(pipeline.image_file.path,"r") as zip_ref:
            zip_ref.extractall(root_path)
        
        # Load manifest
        try:
            with open(os.path.join(root_path, "manifest.json"), "r") as f:
                data = f.read()
                manifest = json.loads(data)
                if "documents" in manifest.keys():
                    pipeline.documents = manifest.pop("documents")
                    for k in pipeline.documents.keys():
                        pipeline.documents[k] = os.path.join(root_path, pipeline.documents[k])
                if "developpers" in manifest.keys():
                    pipeline.developpers = manifest.pop("developpers")
                if "api" in manifest.keys():
                    pipeline.version_api = manifest.pop("api")
                pipeline.manifest = manifest 
                pipeline.save()
        except Exception as ex:
            pipeline.status = "error"
            pipeline.save()
            raise RegovarException("Unable to open and read manifest.json. The pipeline package is wrong or corrupt.", "", ex)
        
        # Check that pipeline type is supported
        if "type" not in manifest.keys():
            pipeline.status = "error"
            pipeline.save()
            raise RegovarException("Pipeline virtualization type not specified. Installation aborded.")
        pipeline.type = manifest["type"]
        pipeline.installation_date = datetime.datetime.now()
        pipeline.status = "installing"
        pipeline.save()
        if pipeline.type not in CONTAINERS_CONFIG.keys():
            pipeline.status = "error"
            pipeline.save()
            raise RegovarException("Container manager of type {} not supported by the server.".format(pipeline.type))
        
        # Install pipeline according to the type
        try:
            result = core.container_managers[pipeline.type].install_pipeline(pipeline)
        except Exception as ex:
            if isinstance(ex, RegovarException): raise ex
            raise RegovarException("Error occured during installation of the pipeline. Installation aborded.", "", ex)







    def delete(self, pipeline_id, asynch=True):
        """
            Start the uninstallation of the pipeline. (done in another thread)
            Remove image file if exists.
        """
        from core.core import core

        result = None
        pipeline = Pipeline.from_id(pipeline_id, 1)
        if pipeline:
            result = pipeline.to_json()
            # Clean container
            try:
                if asynch: 
                    run_async(self.__delete, pipeline) 
                else: 
                    self.__delete(pipeline)
            except Exception as ex:
                err("core.PipelineManager.delete : Container manager failed to delete the pipeline with id {}." + str(pipeline.id), ex)
            try:
                # Clean filesystem
                shutil.rmtree(pipeline.path, True)
                # Clean DB
                core.files.delete(pipeline.image_file_id)
                Pipeline.delete(pipeline.id)
            except Exception as ex:
                raise RegovarException("core.PipelineManager.delete : Unable to delete the pipeline's pirus data for the pipeline {}." + str(pipeline.id), ex)
        return result


    def __delete(self, pipeline):
        from core.core import core
        
        try:
            core.container_managers[pipeline.type].uninstall_pipeline(pipeline)
        except Exception as ex:
            raise RegovarException("Error occured during uninstallation of the pipeline. Uninstallation aborded.", ex)
 
