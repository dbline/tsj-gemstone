from django.db import models, connection

def list_to_dict(row_list):
    result_list = []
    for record in row_list:
        name = None
        if len(record) == 4:
            id, abbr, name, aliases = record
        else:
            id, abbr, aliases = record
        id = int(id)
        abbr = abbr.strip().upper()
        aliases = aliases.splitlines()

        #Append the primary element to the result list then loop through all of the aliases and names and do the same
        result_list.append((abbr, id))
        for alias in aliases:
            alias = alias.strip().upper()
            if alias: result_list.append((alias, id))
        if name:
            result_list.append((name.strip().upper(), id))

    return dict(result_list)

def list_to_dict_disabled(row_list):
    result_list = []
    for record in row_list:
        name, disabled = None, None
        record_len = len(record)
        if record_len == 5:
            id, abbr, name, disabled, aliases = record
        elif record_len == 4:
            id, abbr, name, aliases = record
        else:
            id, abbr, aliases = record
        id = int(id)
        abbr = abbr.strip().upper()
        aliases = aliases.splitlines()

        #Append the primary element to the result list then loop through all of the aliases and names and do the same
        result_list.append((abbr, (id, disabled)))
        for alias in aliases:
            alias = alias.strip().upper()
            if alias: result_list.append((alias, (id, disabled)))
        if name:
            result_list.append((name.strip().upper(), (id, disabled)))

    return dict(result_list)

class DictManager(models.Manager):
    def as_dict(self):
        cursor = connection.cursor()
        try:
            name_field = self.model._meta.get_field('name')
            cursor.execute('SELECT id, abbr, name, aliases FROM %s;' % self.model._meta.db_table)
        except:
            cursor.execute('SELECT id, abbr, aliases FROM %s;' % self.model._meta.db_table)
        return list_to_dict(cursor.fetchall())

    def as_dict_disabled(self):
        cursor = connection.cursor()
        try:
            disabled_field = self.model._meta.get_field('disabled')
            cursor.execute('SELECT id, abbr, name, disabled, aliases FROM %s;' % self.model._meta.db_table)
        except:
            try:
                name_field = self.model._meta.get_field('name')
                cursor.execute('SELECT id, abbr, name, aliases FROM %s;' % self.model._meta.db_table)
            except:
                cursor.execute('SELECT id, abbr, aliases FROM %s;' % self.model._meta.db_table)
        return list_to_dict_disabled(cursor.fetchall())
