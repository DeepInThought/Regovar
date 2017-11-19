#!env/python3
# coding: utf-8
import ipdb

from core.framework.common import log, war, err




class AbstractVariantExporter():
    def __init__(self):
        # Description of the export script.
        metadata = {
            "name" : "CSV", # name of the import manager
            "output" :  ["csv", "tsv"],  # list of file extension that manage the export manager
            "description" : "Export variants into a flat file with columns separeted by comma (CSV) or tab (TSV)" # short desciption about what it does
        }

    @staticmethod
    async def export_data(analysis_id, **kargs):
        raise NotImplementedError("The abstract method \"export_data\" of AbstractVariantExporter must be implemented.")






        
        