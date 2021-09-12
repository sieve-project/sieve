import sqlite3
import json
import analyze_util
from common import sieve_modes

#     conn = analyze_sql.create_sqlite_db()
#     analyze_sql.record_event_list_in_sqlite(event_list, conn)
#     analyze_sql.record_side_effect_list_in_sqlite(side_effect_list, conn)
#     cur = conn.cursor()
#     query = analyze_sql.passes_as_sql_query(analysis_mode)
#     print("Running SQL query as below ...")
#     print(query)
#     cur.execute(query)
#     rows = cur.fetchall()
#     for row in rows:
#         event_id = row[0]
#         side_effect_id = row[1]
#         reduced_event_effect_pairs.append(
#             [event_id_map[event_id], side_effect_id_map[side_effect_id]])

SQL_BASE_PASS_QUERY = "select e.sieve_event_id, se.sieve_side_effect_id from events e join side_effects se on se.range_start_timestamp < e.event_cache_update_time and se.range_end_timestamp > e.event_arrival_time"
SQL_DELETE_ONLY_FILTER = "se.event_type = 'Delete'"
SQL_ERROR_MSG_FILTER = "se.error = 'NoError'"
SQL_WRITE_READ_FILTER = "(exists(select * from json_each(se.read_fully_qualified_names) where json_each.value = e.fully_qualified_name) or exists(select * from json_each(se.read_types) where json_each.value = e.resource_type))"


def create_sqlite_db():
    database = "/tmp/test.db"
    conn = sqlite3.connect(database)
    conn.execute("drop table if exists events")
    conn.execute("drop table if exists side_effects")

    # TODO: SQlite3 does not type check by default, but
    # tighten the column types later
    conn.execute(
        """
        create table events
        (
           id integer not null primary key,
           sieve_event_id integer not null,
           event_type text not null,
           resource_type text not null,
           json_object text not null,
           namespace text not null,
           name text not null,
           event_arrival_time integer not null,
           event_cache_update_time integer not null,
           fully_qualified_name text not null
        )
    """
    )
    conn.execute(
        """
        create table side_effects
        (
           id integer not null primary key,
           sieve_side_effect_id integer not null,
           event_type text not null,
           resource_type text not null,
           namespace text not null,
           name text not null,
           error text not null,
           read_types text not null,
           read_fully_qualified_names text not null,
           range_start_timestamp integer not null,
           range_end_timestamp integer not null,
           end_timestamp integer not null,
           owner_controllers text not null
        )
    """
    )
    return conn


def record_event_list_in_sqlite(event_list, conn):
    for e in event_list:
        json_form = json.dumps(e.obj)
        # Skip the first column: Sqlite will use an auto-incrementing ID
        conn.execute(
            "insert into events values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                None,
                e.id,
                e.etype,
                e.rtype,
                json_form,
                e.namespace,
                e.name,
                e.start_timestamp,
                e.end_timestamp,
                e.key,
            ),
        )
    conn.commit()


def record_side_effect_list_in_sqlite(side_effect_list, conn):
    for e in side_effect_list:
        json_read_types = json.dumps(list(e.read_types))
        json_read_keys = json.dumps(list(e.read_keys))
        json_owner_controllers = json.dumps(list(e.owner_controllers))
        # Skip the first column: Sqlite will use an auto-incrementing ID
        conn.execute(
            "insert into side_effects values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                None,
                e.id,
                e.etype,
                e.rtype,
                e.namespace,
                e.name,
                e.error,
                json_read_types,
                json_read_keys,
                e.range_start_timestamp,
                e.range_end_timestamp,
                e.end_timestamp,
                json_owner_controllers,
            ),
        )
    conn.commit()


def passes_as_sql_query(analysis_mode):
    query = SQL_BASE_PASS_QUERY
    first_optional_pass = True
    if (
        analyze_util.DELETE_ONLY_FILTER_FLAG
        and analysis_mode == sieve_modes.TIME_TRAVEL
    ):
        query += " where " if first_optional_pass else " and "
        query += SQL_DELETE_ONLY_FILTER
        first_optional_pass = False
    if analyze_util.ERROR_MSG_FILTER_FLAG:
        query += " where " if first_optional_pass else " and "
        query += SQL_ERROR_MSG_FILTER
        first_optional_pass = False
    if analyze_util.WRITE_READ_FILTER_FLAG:
        query += " where " if first_optional_pass else " and "
        query += SQL_WRITE_READ_FILTER
        first_optional_pass = False
    return query
