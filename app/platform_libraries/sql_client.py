# -*-coding: utf-8 -*-
""" SQLite client.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sqlite3
# platform modules
import common_utils


class SQLite(object):
    def __init__(self, db_file, timeout=60*5):
        self.conn = sqlite3.connect(db_file, timeout)
        self.conn.row_factory = self.dict_factory
        self.cursor = self.conn.cursor()

    def __del__(self):
        self.cursor.close()
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.__del__()
        if type: # Raise exception out.
            raise type, value, traceback

    def dict_factory(self, cursor, row):
        row_dict = {}
        for idx, column in enumerate(cursor.description):
            row_dict[column[0]] = row[idx]
        return row_dict


class FileDatabase(SQLite):

    def __init__(self, db_file, table, timeout=60*5):
        self.table = table
        self.log = common_utils.create_logger(root_log='KAT.filedatabase')
        SQLite.__init__(self, db_file, timeout)

    def execute(self, sql, ret_filed=None, has_total=True, convert_func=None):
        self.log.debug(u"SQL: {}".format(sql))
        # Send request
        cur = self.cursor.execute(sql)
        row = cur.fetchone()
        # Check row counts.
        if has_total:
            self.log.debug("rowcount: {}".format(row['total']))
            if not row['total']: # SQLite need count ourself.
                self.log.debug("Data not found in database.")
                return None
        # Fetch only one field if filed name is given.
        if ret_filed:
            row = row[ret_filed]
        # Convert data if need.
        if convert_func:
            try:
                return convert_func(row)
            except Exception as e:
                self.log.warning("Data is not correct: {}".format(e), exc_info=True)
                return None
        # Return all.
        return row


class ThumbnailsDatabase(FileDatabase):

    def __init__(self, db_file, table='thumbnails', timeout=60*5):
        FileDatabase.__init__(self, db_file, table, timeout)

    def get_file_by_name(self, filename, size=None, ret_all=False, filename_field='filename'):
        sql = u"""
            SELECT *, COUNT(*) as total
            FROM   {0}
            WHERE  {1} == "{2}"{3};
        """.format(self.table, filename_field, filename, ' AND size="{}"'.format(size) if size else '')
        return self.execute(sql, None if ret_all else 'thumb_path')

    def get_file_by_path(self, filepath, size=None, ret_all=False, filepath_field='src_path'):
        sql = u"""
            SELECT *, COUNT(*) as total
            FROM   {0}
            WHERE  {1} == "{2}"{3};
        """.format(self.table, filepath_field, filepath, ' AND size="{}"'.format(size) if size else '')
        return self.execute(sql, None if ret_all else 'thumb_path')
