 
#!env/python3
# coding: utf-8
import ipdb; 


import os
import json
import aiohttp
import aiohttp_jinja2
import datetime
import time


from aiohttp import web, MultiDict
from urllib.parse import parse_qsl

from config import *
from core.framework.common import *
from core.framework.tus import *
from core.model import *
from api_rest.rest import *





# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# PROJECT HANDLER
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 





class ProjectHandler:
    def list(self, request):
        """
            Get list of all projects (allow search parameters)
        """
        from core.core import core
        fields, query, order, offset, limit = process_generic_get(request.query_string, Project.public_fields)
        depth = int(MultiDict(parse_qsl(request.query_string)).get('depth', 0))
        # Get range meta data
        range_data = {
            "range_offset" : offset,
            "range_limit"  : limit,
            "range_total"  : Project.count(),
            "range_max"    : RANGE_MAX,
        }
        projects = core.projects.get(fields, query, order, offset, limit, depth)
        return rest_success([p.to_json() for p in projects], range_data)
        
    
    async def create_or_update(self, request):
        """
            Create or update a project with provided data
        """
        from core.core import core
        data = await request.json()
        if isinstance(data, str) : data = json.loads(data)
        # Create the project
        try:
            project = core.projects.create_or_update(data, 1)
        except RegovarException as ex:
            return rest_exception(ex)
        if project is None:
            return rest_error("Unable to create a new project.")
        return rest_success(project.to_json())
        
        
    def get(self, request):
        """
            Get details about the project
        """
        project_id = request.match_info.get('project_id', -1)
        project = Project.from_id(project_id, 1)
        if not project:
            return rest_error("Unable to find the project (id={})".format(project_id))
        return rest_success(project.to_json(Project.public_fields))
        
    
    
    
    def delete(self, request):
        """
            Delete the project
        """
        from core.core import core
        project_id = request.match_info.get('project_id', -1)
        project = core.Project.delete(project_id, 1)
        if not project:
            return rest_error("Unable to delete the project (id={})".format(project_id))
        return rest_success(project.to_json(Project.public_fields))
    
    
    
    def events(self, request):
        """
            Get list of events of the project (allow search parameters)
        """
        from core.core import core
        fields, query, order, offset, limit = process_generic_get(request.query_string, Project.public_fields)
        project_id = request.match_info.get('project_id', -1)
        depth = int(MultiDict(parse_qsl(request.query_string)).get('depth', 0))
        # Get range meta data
        range_data = {
            "range_offset" : offset,
            "range_limit"  : limit,
            "range_total"  : Project.count(),
            "range_max"    : RANGE_MAX,
        }
        events = core.events.get(fields, query, order, offset, limit, depth)
        return rest_success([e.to_json() for e in events], range_data)


    def subjects(self, request):
        """
            Get list of subjects of the project (allow search parameters)
        """
        from core.core import core
        fields, query, order, offset, limit = process_generic_get(request.query_string, Project.public_fields)
        project_id = request.match_info.get('project_id', -1)
        depth = int(MultiDict(parse_qsl(request.query_string)).get('depth', 0))
        # Get range meta data
        range_data = {
            "range_offset" : offset,
            "range_limit"  : limit,
            "range_total"  : Project.count(),
            "range_max"    : RANGE_MAX,
        }
        subjects = core.subjects.get(fields, query, order, offset, limit, depth)
        return rest_success([s.to_json() for s in subjects], range_data)
    
    
    def tasks(self, request):
        """
             Get list of tasks (jobs and analyses) of the project (allow search parameters)
        """
        from core.core import core
        fields, query, order, offset, limit = process_generic_get(request.query_string, Project.public_fields)
        depth = int(MultiDict(parse_qsl(request.query_string)).get('depth', 0))
        # Get range meta data
        range_data = {
            "range_offset" : offset,
            "range_limit"  : limit,
            "range_total"  : Project.count(),
            "range_max"    : RANGE_MAX,
        }
        jobs = core.jobs.get(fields, query, order, offset, limit, depth)
        analyses = core.analyses.get(fields, query, order, offset, limit, depth)
        tasks = array_merge(jobs, analyses)
        return rest_success([t.to_json() for t in tasks], range_data)


    def files(self, request):
        """
            Get list of subjects of the project (allow search parameters)
        """
        from core.core import core
        fields, query, order, offset, limit = process_generic_get(request.query_string, Project.public_fields)
        project_id = request.match_info.get('project_id', -1)
        depth = int(MultiDict(parse_qsl(request.query_string)).get('depth', 0))
        # Get range meta data
        range_data = {
            "range_offset" : offset,
            "range_limit"  : limit,
            "range_total"  : Project.count(),
            "range_max"    : RANGE_MAX,
        }
        files = core.files.get(fields, query, order, offset, limit, depth)
        return rest_success([f.to_json() for f in files], range_data)
    
    











