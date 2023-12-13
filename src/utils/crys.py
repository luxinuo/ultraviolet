#!/usr/bin/python3
# -*- coding: utf-8 -*- #


from psql import PSQL

# import subprocess
import argparse
import requests
import json
import os
import yaml
from urllib.parse import unquote

# import time

from typing import List

# import pandas as pd
# import numpy as np


class Crystal(PSQL):
    URL = "service=meta"

    def __init__(
        self,
        ip,
        conn_info="",
        schema="crystaldb",
        port="5555",
        cls=None,
        is_remote=False,
        pro_url=None,
        ceq_dev=False,
    ):
        self.schema = schema
        self.ip = ip
        self.conn_info = conn_info
        self.schema = schema
        self.port = port
        self.cls = cls
        self.is_remote = is_remote
        self.pro_url = pro_url
        self.ceq_dev = ceq_dev
        self.admin_ip = None

    def conn_string(self, dba_secret: str = ""):
        if self.is_remote and dba_secret != "":
            self.conn_info = (
                f"postgresql://dbuser_dba:{dba_secret}@{self.ip}:{self.port}/meta"
            )
            return self.conn_info
        elif self.ip == "meta" and self.is_remote == False:
            self.conn_info = "service=meta"
            return self.conn_info
        else:
            self.conn_info = "service=meta"
            return self.conn_info

    def cct_conn(self) -> None:
        if not self.conn_info:
            raise Exception("No connection info(conn_info) provided.")
        else:
            PSQL.__init__(self, url=self.conn_info)
            # print("Connection success!")

    def list(self):
        sql = "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = '{0}'".format(
            self.schema
        )
        return self.fetch_column(sql)

    def get_admin_ip(self):
        """Get admin ip from CCT meta."""
        if not self.admin_ip:
            admin_ip = self.call("crystaldb.get_param", ("admin_ip",))[0][0]
            self.admin_ip = admin_ip
            return admin_ip
        else:
            return self.admin_ip

    def summary(self):
        if self.schema == "crystaldb":
            tables = ["group", "group_var", "host", "host_var"]
            for tbl in tables:
                table = f"{self.schema}.{tbl}"
                print("Table name:", table)
                result_list = self.glimpse(table=table, limit=22)
                # print([v for v in query_result])
                dic = {"group": 1, "group_var": 3, "host": 2, "host_var": 4}

                for v in result_list:
                    print(v[: dic[tbl]])
                print("---" * 22)
        else:
            pass

    def cct_groups_info(self):
        """Get all clusters info in list and set groups attribute."""
        if self.conn_info and self.url:
            result = self.fetch_column(sql=f"select cls from {self.schema}.group")
            self.groups = result if result else []
        else:
            raise Exception("No connection info(conn_info) provided.")
        return result

    def cct_groups(self):
        if self.cls and self.schema == "crystaldb":
            result = self.fetch_column(
                sql=f"select cls from {self.schema}.group where cls = '{self.cls}'"
            )
        elif self.schema == "crystaldb":
            result = self.fetch_column(sql=f"select cls from {self.schema}.group")
        else:
            raise Exception("Schema is not crystaldb and we are not supporting it yet.")
        return result if result else f"group {self.cls} is not found in CCT."

    def set_group(self, cls_name: str, add_new=True):
        self.groups = self.cct_groups_info()
        print("All Groups:", self.groups)
        result = self.fetch_column(
            sql=f"select cls from {self.schema}.group where cls = '{cls_name}'"
        )
        if result:
            self.cls = cls_name
            print(f"Group {cls_name} is set.")
        else:
            if add_new == False:
                print(
                    f"Group {cls_name} is not found in CCT. Consider to add it first."
                )
            else:
                print(f"Adding group for {cls_name}")
                self.add_group(cls_name=cls_name)

    def add_group(self, cls_name: str):
        self.insert("crystaldb.group", ["cls"], [cls_name])
        self.insert(
            "crystaldb.group_var",
            ["cls", "key", "value"],
            [cls_name, "pg_cluster", json.dumps(cls_name)],
        )
        self.cls = cls_name if not self.cls else self.cls
        print("Success! Return the cls atrribute for you:", self.cls)

    def del_group(self):
        if self.cls:
            sql = "delete from crystaldb.group where cls = %s"
            del_group_name = self.cls
            print("Delete group:", del_group_name)
            self.cls = None
            self.host_ips = None
            return self.execute(sql, (del_group_name,))
        else:
            raise Exception("No cls provided, please set cls attribute.")

    def del_groups(self, cls_list: List[str]):
        sql = "delete from crystaldb.group where cls = %s"
        for g in cls_list:
            print("Delete group:", g)
            self.execute(sql, (g,))

    def cct_hosts(self) -> List[str]:
        """Remeber to set cls attribute first."""
        if self.cls:
            result = self.fetch_column(
                sql=f"select ip from {self.schema}.host where cls = '{self.cls}'"
            )
            self.host_ips = result if result else []
            return result
        else:
            print(
                "Warning: No cls provided, return all hosts but not set the host_ips atrribute:"
            )
            return self.fetch_column(sql=f"select distinct ip from {self.schema}.host")

    def max_seq(self, cls_name=None):
        if cls_name:
            sql = f"select max(value::int) from crystaldb.host_var where cls = '{cls_name}' and key = 'pg_seq'"
        elif self.cls:
            sql = f"select max(value::int) from crystaldb.host_var where cls = '{self.cls}' and key = 'pg_seq'"
        else:
            raise Exception("No cls provided, please set cls attribute.")
        result = self.fetch_column(sql)[0]
        return result if result else 0

    def add_hosts(self, new_hosts: List[str]) -> List[str]:
        """Remeber to set cls attribute first."""
        result = []
        if self.cls:
            seq = self.max_seq(self.cls) + 1
            for h in new_hosts:
                condition = f"cls = '{self.cls}' and key = 'pg_role' and  value = '{json.dumps('primary')}'"
                print(condition)

                primary_role_cnt = self.count("crystaldb.host_var", condition)
                if seq == 1 or primary_role_cnt == 0:
                    role = "primary"
                else:
                    role = "replica"

                self.insert("crystaldb.host", ["cls", "ip"], [self.cls, h])
                self.insert(
                    "crystaldb.host_var",
                    ["cls", "ip", "key", "value"],
                    [self.cls, h, "pg_seq", json.dumps(seq)],
                )
                self.insert(
                    "crystaldb.host_var",
                    ["cls", "ip", "key", "value"],
                    [self.cls, h, "pg_role", json.dumps(role)],
                )
                print(seq)
                result.append(h)
                seq += 1
        return result

    def del_host(self, del_hosts: List[str]):
        if self.cls and self.host_ips:
            ip_result = "'" + "', '".join(del_hosts) + "'"
            sql = f"delete from crystaldb.host where cls = '{self.cls}' and ip in ({ip_result})"
            print(sql)
            return self.execute(sql=sql)
        else:
            raise Exception(
                "No cls or hosts_ips provided, please set cls and hosts_ips attribute."
            )

    def get_inv(self):
        """Get inventory from CCT."""
        result = self.glimpse(table="crystaldb.inventory")
        self.inventory = result[0][0]
        return self.inventory

    def set_inv(self):
        """Set inventory attribute from CCT meta."""
        result = self.glimpse(table="crystaldb.inventory")
        self.inventory = result[0][0]
        print("Done setting inventory attribute!!!")

    def group_conf(self):
        """Get group config from CCT."""
        result = self.glimpse(table="crystaldb.group_config")
        if self.cls:
            for v in result:
                if v[0] == self.cls:
                    self.g_vars = v[2]
                    self.h_vars = v[1]
                    print(list(v))
        else:
            print(result)

    # def group_2_df(self, tbl: str = "group_var"):
    #     cols = self.desc(table=tbl, schema=self.schema)
    #     cols = [c[1] for c in cols]
    #     result = self.glimpse(table=self.schema + "." + tbl)
    #     df_group = pd.DataFrame(result, columns=cols)
    #     return df_group

    def create_proc_fs(self):
        """Create crystaldb.add_fs_ces procedure in CCT."""
        sql = """
        CREATE OR REPLACE PROCEDURE crystaldb.add_fs_ces(cluster_name text, host_ip inet)
        LANGUAGE plpgsql
        AS $$
        BEGIN
            EXECUTE format($f$
                DROP SERVER IF EXISTS fs_%I CASCADE;
                
                CREATE SERVER fs_%I
                FOREIGN DATA WRAPPER postgres_fdw
                OPTIONS (host %L, port '5555', dbname 'postgres');
                
                ALTER SERVER fs_%I OWNER TO dbuser_dba;
                
                COMMENT ON SERVER fs_%I IS 'Foreign server for %I cluster';
                
                CREATE USER MAPPING FOR dbuser_dba SERVER fs_%I
                OPTIONS (user 'dbuser_dba', password 'DBUser.DBA');
                
                CREATE FOREIGN TABLE crystaldb.pgbackrest_info_%I (
                    data jsonb
                )
                SERVER fs_%I
                OPTIONS (schema_name 'monitor', table_name 'pgbackrest_info');
                
                COMMENT ON FOREIGN TABLE crystaldb.pgbackrest_info_%I IS 'Foreign table for pgbackrest info on %I cluster';
                
                GRANT SELECT ON crystaldb.pgbackrest_info_%I TO dbrole_admin;
                GRANT SELECT ON crystaldb.pgbackrest_info_%I TO dbuser_dba;
                GRANT SELECT ON crystaldb.pgbackrest_info_%I TO dbuser_meta;
                GRANT SELECT ON crystaldb.pgbackrest_info_%I TO dbuser_monitor;
            $f$, 
                cluster_name, -- DROP SERVER
                cluster_name, -- CREATE SERVER
                host_ip, -- CREATE SERVER host option
                cluster_name, -- ALTER SERVER
                cluster_name, cluster_name, -- COMMENT ON SERVER
                cluster_name, -- CREATE USER MAPPING
                cluster_name, -- CREATE FOREIGN TABLE
                cluster_name, -- SERVER option
                cluster_name, cluster_name, -- COMMENT ON FOREIGN TABLE
                cluster_name, -- GRANT SELECT dbrole_admin
                cluster_name, -- GRANT SELECT dbuser_dba
                cluster_name, -- GRANT SELECT dbuser_meta
                cluster_name -- GRANT SELECT dbuser_monitor
            );
        END;
        $$;
        """
        # print(sql)
        return self.execute(sql)

    def alter_fs_host_options(self, new_host, server_name: str = "fs_main"):
        """
        Alter the host option of a foreign server.

        :param server_name: The name of the foreign server to be altered
        :param new_host: The new host value for the foreign server
        """
        sql = """
        ALTER SERVER {0}
        OPTIONS (SET host '{1}');
        """.format(
            server_name, new_host
        )
        return self.execute(sql)

    def bk_info_init(self, fs_name: str = "main"):
        self.create_proc_fs()
        admin_ip = self.call("crystaldb.get_param", ("admin_ip",))[0][0]
        return self.execute("call crystaldb.add_fs_ces(%s, %s)", (fs_name, admin_ip))

    def bk_info(self, tbl_name: str = "monitor.pgbackrest_info"):
        if self.cls:
            sql = f"select * from {tbl_name} limit 1"
            return self.fetch_column(sql)[0]

    def create_view_pgbackrest_info(self):
        query = """
        CREATE OR REPLACE VIEW crystaldb.pgbackrest_new AS
        SELECT z.name,
            jsonb_array_elements.value ->> 'type'::text AS bk_type,
            (jsonb_array_elements.value ->> 'error'::text)::boolean AS bk_error,
            z.current_archive ->> 'min'::text AS wal_min,
            z.current_archive ->> 'max'::text AS wal_max,
            jsonb_array_elements.value ->> 'label'::text AS bk_label,
            jsonb_array_elements.value ->> 'prior'::text AS bk_prior,
            ((jsonb_array_elements.value -> 'timestamp'::text) ->> 'start'::text)::numeric AS bk_start_ts,
            ((jsonb_array_elements.value -> 'timestamp'::text) ->> 'stop'::text)::numeric AS bk_stop_ts,
            to_timestamp((((jsonb_array_elements.value -> 'timestamp'::text) ->> 'start'::text)::numeric)::double precision) AS bk_start_at,
            to_timestamp((((jsonb_array_elements.value -> 'timestamp'::text) ->> 'stop'::text)::numeric)::double precision) AS bk_stop_at,
            (jsonb_array_elements.value -> 'lsn'::text) ->> 'start'::text AS bk_start_lsn,
            (jsonb_array_elements.value -> 'lsn'::text) ->> 'stop'::text AS bk_stop_lsn,
            ((jsonb_array_elements.value -> 'info'::text) ->> 'size'::text)::bigint AS bk_size,
            ((jsonb_array_elements.value -> 'info'::text) ->> 'delta'::text)::bigint AS bk_delta,
            (((jsonb_array_elements.value -> 'info'::text) -> 'repo'::text) ->> 'size'::text)::bigint AS bk_repo_size,
            (((jsonb_array_elements.value -> 'info'::text) -> 'repo'::text) ->> 'delta'::text)::bigint AS bk_repo_delta,
            jsonb_array_elements.value -> 'reference'::text AS bk_reference,
            jsonb_array_elements.value -> 'annotation'::text AS bk_annotation
        FROM ( SELECT jsonb_array_elements_1.value ->> 'name'::text AS name,
                    jsonb_array_elements_1.value -> 'backup'::text AS backups,
                    (jsonb_array_elements_1.value -> 'archive'::text) -> (jsonb_array_length(jsonb_array_elements_1.value -> 'archive'::text) - 1) AS current_archive
                FROM crystaldb.pgbackrest_info_main i,
                    LATERAL jsonb_array_elements(i.data) jsonb_array_elements_1(value)) z,
            LATERAL jsonb_array_elements(z.backups) jsonb_array_elements(value);
        """
        return self.execute(query)

    def create_tmp_bk_info_table(self):
        """
        Creates the table crystaldb.tmp_bk_info if it does not exist, or truncates it if it does.
        The table will have columns: cls (text), data (jsonb), ctime (timestamp with time zone).
        """
        # Check if table exists
        table_exists_query = """
        SELECT EXISTS (
            SELECT FROM pg_tables 
            WHERE  schemaname = 'crystaldb' 
            AND    tablename  = 'tmp_bk_info'
        );
        """
        if self.fetch_scale(table_exists_query):
            # Truncate the table if it exists
            truncate_sql = "TRUNCATE TABLE crystaldb.tmp_bk_info;"
            # print(truncate_sql)
            return self.execute(truncate_sql)
        else:
            # Create the table if it does not exist
            create_sql = """
            CREATE TABLE crystaldb.tmp_bk_info (
                cls TEXT,
                data JSONB,
                ctime TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """
            # print(create_sql)
            return self.execute(create_sql)

    def insert_bk_table(self):
        """
        Inserts the latest pgbackrest info into the table crystaldb.tmp_bk_info.
        """
        # Get the latest pgbackrest info
        bk_json = self.bk_info()
        # Insert the info into the table
        insert_sql = """
        INSERT INTO crystaldb.tmp_bk_info (cls, data)
        VALUES (%s, %s);
        """
        self.execute(insert_sql, (self.cls, json.dumps(bk_json)))

    def get_leaders(self, metric: str = "patroni_master==1", quiet: bool = False):
        self.target_ip = self.ip if self.is_remote == True else "127.0.0.1"
        api_endpoint = f"http://{self.target_ip}:9090"
        pro_url = f"{api_endpoint}/api/v1/query"
        params = {
            "query": metric,
        }

        try:
            response = requests.get(pro_url, params=params)
            if response.status_code == 200:
                # Parse the JSON response.
                response_data = response.json()
                # print(json.dumps(response_data, indent=4))
            else:
                return f"Error: {response.status_code}"
        except Exception as e:
            return f"Error: {str(e)}"

        result = json.dumps(response_data.get("data").get("result"))
        if quiet == True:
            return [v.get("metric").get("ip") for v in json.loads(result)]
        else:
            return result

    def met_json(self, metric: str):
        self.target_ip = self.ip if self.is_remote == True else "127.0.0.1"
        api_endpoint = f"http://{self.target_ip}:9090"
        pro_url = f"{api_endpoint}/api/v1/query"
        params = {
            "query": metric,
        }

        try:
            response = requests.get(pro_url, params=params)
            if response.status_code == 200:
                # Parse the JSON response.
                response_data = response.json()
                # print(json.dumps(response_data, indent=4))
            else:
                return f"Error: {response.status_code}"
        except Exception as e:
            return f"Error: {str(e)}"

        result = json.dumps(response_data.get("data").get("result"))
        return result

    def lux_dev(self):
        if self.ceq_dev == True and self.is_remote == True:
            self.target_ip = self.ip
            self.dev_remote_ip = self.ip
            self.conn_info = (
                f"postgresql://dbuser_dba:DBUser.DBA@{self.target_ip}:5555/meta"
            )
            return self.conn_info

    def get_db(self):
        if self.cls:
            sql = "SELECT value from crystaldb.group_var where cls = %s and key = 'pg_databases';"
            return self.fetch(sql, (self.cls,))[0][0]

    def add_og_db(self, dbname: str, default: bool = True, schema_name: str = ""):
        if self.cls and dbname and default:
            db_template = json.dumps(
                [
                    {
                        "name": dbname,
                        "comment": "",
                        "schemas": [schema_name],
                        "baseline": "",
                        "extensions": [],
                    }
                ]
            )
            print(db_template)
            return self.insert(
                table="crystaldb.group_var",
                columns=["cls", "key", "value"],
                value=[self.cls, "pg_databases", db_template],
            )
        else:
            raise Exception(
                "No cls or dbname provided, please set cls attribute and dbname argument."
            )

    def del_db(self, del_all: bool = True):
        if self.cls:
            if del_all:
                sql = "delete from crystaldb.group_var where cls = %s and key = 'pg_databases';"
                return self.execute(sql, (self.cls,))
            else:
                pass
        else:
            pass

    def get_cron(self):
        if self.cls:
            sql = "SELECT value from crystaldb.group_var where cls = %s and key = 'node_crontab';"
            return self.fetch(sql, (self.cls,))[0][0]

    def add_og_cron(self, add_default: bool = True, custom_cron: str = None):
        """Works if you have set your cls attribute and you haven't set the crontab key in this cluster"""
        if self.cls:
            if add_default == True:
                cron_json_str = json.dumps(
                    ["00 01 * * * postgres /opt/CrystalDB/bin/pg-backup full"]
                )
                print(cron_json_str)
                return self.insert(
                    "crystaldb.group_var",
                    ["cls", "key", "value"],
                    [self.cls, "node_crontab", cron_json_str],
                )
            else:
                if custom_cron:
                    cron_json_str = json.dumps(custom_cron)
                    print(cron_json_str)
                    return self.insert(
                        "crystaldb.group_var",
                        ["cls", "key", "value"],
                        [self.cls, "node_crontab", cron_json_str],
                    )
                else:
                    raise Exception(
                        "No custom_cron provided. Please provide json arry string in custom_cron."
                    )

    def del_cron(self, del_all: bool = True):
        if self.cls:
            if del_all:
                sql = "delete from crystaldb.group_var where cls = %s and key = 'node_crontab';"
                return self.execute(sql, (self.cls,))
            else:
                pass
        else:
            pass

    def update_cron(self, cron_val: str, is_encode_url: bool = True):
        """Seperate cron_val using sep and in each item the space symbol equal to space_symbol"""

        result = []
        sql = "update crystaldb.group_var set value = %s where cls = %s and key = 'node_crontab';"
        if self.cls and cron_val == "null":
            result_null = json.dumps(result)
            return self.execute(sql, (result_null, self.cls))
        elif self.cls and cron_val == "template":
            cron_json_str = json.dumps(
                ["00 01 * * * postgres /opt/CrystalDB/bin/pg-backup full"]
            )
            return self.execute(sql, (cron_json_str, self.cls))
        elif self.cls and is_encode_url == True:
            decoded_url = unquote(cron_val)
            print(decoded_url)
            return self.execute(sql, (decoded_url, self.cls))
        else:
            pass

    def get_meta(self) -> dict:
        """Get meta info from CCT meta, if inventory attribute is not set, it will set it first and get data"""
        self.set_inv()
        result_dic = self.inventory
        return result_dic

    def get_meta_ip_key(self, host_ip: str):
        """Get specific ip keys from  the cluster you set"""
        if self.cls:
            result_list = self.cct_hosts()
            print(result_list)
            print(
                host_ip
                if host_ip in result_list
                else f"{host_ip} is not in this cluster."
            )
        else:
            pass

    def cmdb_citus(
        self,
        new_host_ip: str,
        cluster: str = "pg-citus",
        user_name: str = "test",
        user_password: str = "test",
        dbname: str = "test",
    ):
        """Add citus new cluster with new host ip, if cluster contains -- means that we are gonna add new ip into already existed cluster, else means we are gonna create a new clitus cluster"""

        groups_info = self.cct_groups_info()
        print(groups_info)

        if cluster in groups_info:
            # cuz the cluster is already existed, we will add new host into it
            self.set_group(cluster)
            self.add_hosts([new_host_ip])
            return f"Adding host into cluster {cluster} Done!"

        # Dealing with sequence number
        citus_index = cluster.find("--")

        if citus_index == -1:
            # symbol not found which means that we will add a worker or a coordinator cluster(seq=0)
            result_seq_list = [
                int(group.replace(cluster + "--", ""))
                for group in groups_info
                if group.startswith(cluster + "--")
            ]
            print(result_seq_list)
            if not result_seq_list:
                # adding coordinator cluster which is cluster + "--" + 0
                seq = 0
            elif 0 not in result_seq_list:
                seq = 0
            else:
                # adding worker cluster
                seq = max(result_seq_list) + 1
        else:
            # in this case shall not happen cuz if -- appear the cluster should equal the citus cluster, adding host and return
            pass

        print(cluster)

        citus_name = cluster + "--" + str(seq)
        print(citus_name)
        default_data = {
            "pg_group": seq,
            "pg_mode": "citus",
            "pg_shard": cluster,
            "patroni_citus_db": dbname,
            "pg_dbsu_password": "DBUser.Postgres",
            "pg_libs": "citus, timescaledb, pg_stat_statements, auto_explain",
            "pg_users": [
                {
                    "name": user_name,
                    "roles": ["dbrole_admin"],
                    "password": user_password,
                    "pgbouncer": True,
                }
            ],
            "pg_databases": [
                {
                    "name": dbname,
                    "owner": "citus",
                    "extensions": [
                        {"name": "citus"},
                        {"name": "postgis"},
                        {"name": "timescaledb"},
                    ],
                }
            ],
            "pg_hba_rules": [
                {
                    "db": "all",
                    "addr": self.get_admin_ip() + "/24",
                    "auth": "trust",
                    "user": "all",
                    "title": "trust citus cluster members",
                },
                {
                    "db": "all",
                    "addr": "127.0.0.1/32",
                    "auth": "ssl",
                    "user": "all",
                    "title": "all user ssl access from localhost",
                },
                {
                    "db": "all",
                    "addr": "intra",
                    "auth": "ssl",
                    "user": "all",
                    "title": "all user ssl access from intranet",
                },
            ],
            "node_crontab": ["00 01 * * * postgres /opt/CrystalDB/bin/pg-backup full"],
        }

        if citus_name not in groups_info:
            # Initialize the cluster, insert into group table
            self.insert("crystaldb.group", ["cls"], [citus_name])
            self.insert(
                "crystaldb.group_var",
                ["cls", "key", "value"],
                [citus_name, "pg_cluster", json.dumps(citus_name)],
            )

            # Insert default key value in group_var table
            for key, value in default_data.items():
                json_value = json.dumps(value)

                sql_script = f"""
                    INSERT INTO crystaldb.group_var (cls, key, value)
                    VALUES ('{citus_name}', '{key}', '{json_value}'::jsonb);
                """
                self.execute(sql_script)

        self.set_group(citus_name)
        self.add_hosts([new_host_ip])
        print("Done!")

    def add_new_shard(
        self,
        new_host_ip: str,
        cluster_name: str,
        shard_name: str = "pg-citus",
        dbname: str = "test",
        seq: int = 0,
        user_name: str = "test",
        user_password: str = "test"
    ):
        """Add citus new distributed database coordinator in cmdb with new host ip and specific database name"""
        parts = new_host_ip.split('.')
        parts[-1] = '0'
        host_internal_range = '.'.join(parts) + '/24'
        print(host_internal_range)
        
        data = {
            "pg_group": seq,
            "pg_mode": "citus",
            "pg_shard": shard_name,
            "patroni_citus_db": dbname,
            "pg_dbsu_password": "DBUser.Postgres",
            "pg_libs": "citus, timescaledb, pg_stat_statements, auto_explain",
            "pg_users": [
                {
                    "name": user_name,
                    "roles": ["dbrole_admin"],
                    "password": user_password,
                    "pgbouncer": True,
                }
            ],
            "pg_databases": [
                {
                    "name": dbname,
                    "owner": "citus",
                    "extensions": [
                        {"name": "citus"},
                        {"name": "postgis"},
                        {"name": "timescaledb"},
                    ],
                }
            ],
            "pg_hba_rules": [
                {
                    "db": "all",
                    "addr": host_internal_range,
                    "auth": "trust",
                    "user": "all",
                    "title": "trust citus cluster members",
                },
                {
                    "db": "all",
                    "addr": "127.0.0.1/32",
                    "auth": "ssl",
                    "user": "all",
                    "title": "all user ssl access from localhost",
                },
                {
                    "db": "all",
                    "addr": "intra",
                    "auth": "ssl",
                    "user": "all",
                    "title": "all user ssl access from intranet",
                },
            ],
            "node_crontab": ["00 01 * * * postgres /opt/CrystalDB/bin/pg-backup full"],
        }

        self.insert("crystaldb.group", ["cls"], [cluster_name])
        self.insert(
            "crystaldb.group_var",
            ["cls", "key", "value"],
            [cluster_name, "pg_cluster", json.dumps(cluster_name)],
        )
        
        # Insert key value in group_var table for group cluster: cluster_name
        for key, value in data.items():
            json_value = json.dumps(value)
            sql_script = f"""
                INSERT INTO crystaldb.group_var (cls, key, value)
                VALUES ('{cluster_name}', '{key}', '{json_value}'::jsonb);
            """
            self.execute(sql_script)
            
        self.set_group(cluster_name)
        self.add_hosts([new_host_ip])
        
    def get_group_keys(self, target_cls_name: str) -> List[str]:
        return self.fetch_column(sql=f"select key from crystaldb.group_var where cls = '{target_cls_name}'")

    def get_group_var_dic(self, target_cls_name: str):
        result = self.fetch(sql=f"select key, value from crystaldb.group_var where cls = '{target_cls_name}'")
        return {item[0]: item[1] for item in result}

    def shard_info(self) -> None:
        inventory = self.get_inv()
        all_hosts = list(inventory.get('_meta').get('hostvars').keys())
        result = {host: inventory.get('_meta').get('hostvars').get(host).get('pg_shard') for host in all_hosts if 'pg_shard' in inventory.get('_meta').get('hostvars').get(host).keys()}
        print(result)

    def shard_summary(self) -> None:
        shard_result = {}
        inventory = self.get_inv()
        all_hosts = list(inventory.get('_meta').get('hostvars').keys())
        query = "SELECT DISTINCT value FROM crystaldb.group_var where key = 'pg_shard';"
        shard_list = self.fetch_column(sql=query)
        for shard in shard_list:
            shard_result[shard] = [host for host in all_hosts if inventory.get('_meta').get('hostvars').get(host).get('pg_shard') == shard]
        print(shard_result)

    def get_shard_coor(self) -> None:
        shard_result = {}
        inventory = self.get_inv()
        all_hosts = list(inventory.get('_meta').get('hostvars').keys())
        query = "SELECT cls FROM crystaldb.group_var where key = 'pg_group' and value = '0'::jsonb;"
        shard_list = self.fetch_column(sql=query)
        # for shard in shard_list:
            # shard_result[shard] = [host for host in all_hosts if inventory.get('_meta').get('hostvars').get(host).get('pg_shard') == shard]
        print(shard_list)
        
    def shard_max_seq(self, shard_name: str) -> int:
        query = f"select cls from crystaldb.group_var where key = 'pg_shard' and value = '{json.dumps(shard_name)}'"
        
        result = self.fetch_column(sql=query)
        result_str = str(tuple(result)) if len(result) > 1 else f"('{result[0]}')"
        
        # Under same shard has different citus clusters, we are finding the max seq number
        sql = f"select max(value::int) from crystaldb.group_var where cls in {result_str} and key = 'pg_group'"
        # print(sql)
        max_seq = self.fetch_column(sql=sql)[0]
        return max_seq + 1
    
    def shard_has_coordinator(self, shard_name: str) -> bool:
        query = f"select cls from crystaldb.group_var where key = 'pg_shard' and value = '{json.dumps(shard_name)}'"
        result = self.fetch_column(sql=query)
        result_str = str(tuple(result)) if len(result) > 1 else f"('{result[0]}')"
        cond = f"cls in {result_str} and key = 'pg_group' and value = '0'::jsonb"
        cnt = self.count('crystaldb.group_var', cond)
        # print(cnt)
        return True if cnt > 0 else False
    
    def get_coord(self, shard_name: str = ''):
        if shard_name == '':
            # Show all if shard_name is default value
            inv = self.get_inv()
            meta = inv.get('_meta').get('hostvars')
            all_hosts = list(meta.keys())
            shards_dic = {meta.get(host).get('pg_shard'): meta.get(host).get('pg_cluster') for host in all_hosts if 'pg_shard' in meta.get(host).keys() and meta.get(host).get('pg_group') == 0}
            return shards_dic
        else:
            # Show specific shard coordinator
            inv = self.get_inv()
            meta = inv.get('_meta').get('hostvars')
            all_hosts = list(meta.keys())
            shards_dic = {meta.get(host).get('pg_shard'): meta.get(host).get('pg_cluster') for host in all_hosts if 'pg_shard' in meta.get(host).keys() and meta.get(host).get('pg_shard') == f'{json.dumps(shard_name)}' and meta.get(host).get('pg_group') == 0}
            return shards_dic

    
    def add_worker(self, shard_name: str, cluster_name: str, new_ip: str):
        if self.shard_has_coordinator(shard_name) == False:
            # Need to add coordinator first in this shard
            max_seq = 0
            sql = f"select cls from crystaldb.group_var where key = 'pg_shard' and value = '{json.dumps(shard_name)}' limit 1;"
            cls_list = self.fetch_column(sql=sql)
            template_cls_name = cls_list[0]
            # print(template_cls_name)
            
            self.insert("crystaldb.group", ["cls"], [cluster_name])
            
            query = f"""
            INSERT INTO crystaldb.group_var (cls, key, value)
            SELECT '{cluster_name}' as cls, 
            key, 
            case 
                when key = 'pg_group' then '{max_seq}'::jsonb 
                when key = 'pg_cluster' then '{json.dumps(cluster_name)}'
                else value 
                end as value
            FROM crystaldb.group_var
            WHERE cls = '{template_cls_name}'
            """
            self.execute(sql=query)
            self.set_group(cluster_name)
            self.add_hosts([new_ip])
            
        else:
            max_seq = self.shard_max_seq(shard_name)
            coord_dic = self.get_coord()
            coord_cls = coord_dic.get(shard_name)
            
            self.insert("crystaldb.group", ["cls"], [cluster_name])
            
            query = f"""
            INSERT INTO crystaldb.group_var (cls, key, value)
            SELECT '{cluster_name}' as cls, 
            key, 
            case 
                when key = 'pg_group' and value = '0'::jsonb then '{max_seq}'::jsonb 
                when key = 'pg_cluster' then '{json.dumps(cluster_name)}'
                else value 
                end as value
            FROM crystaldb.group_var
            WHERE cls = '{coord_cls}'
            """
            self.execute(sql=query)
            self.set_group(cluster_name)
            self.add_hosts([new_ip])


class CCT:
    def __init__(
        self,
        ip: str,
        username: str = None,
        password: str = None,
        cluster: str = None,
        cookies: requests.cookies.RequestsCookieJar = None,
    ):
        self.ip = ip
        self.username = username
        self.password = password
        self.cookies = cookies
        self.cluster = cluster

    def auth(self, username: str, password: str):
        self.username = username
        self.password = password
        print(f"Your auth: {self.username}")
        print(f"Your password: {self.password}")
        api_url = f"http://{self.ip}/cct/api/auth/login"
        return api_url

    def post_auth(self, endpoint: str = "api/auth/login"):
        """post request"""

        complete_url = f"http://{self.ip}/cct/{endpoint}"
        headers = {"Content-Type": "application/json"}
        data = {"auth": self.username, "password": self.password}
        print(complete_url)
        # try:
        #     response = requests.post(complete_url, data=json.dumps(data), headers=headers)

        #     response.raise_for_status()
        #     return response.json()
        # except requests.exceptions.HTTPError as errh:
        #     return f"Http Error: {errh}"
        # except requests.exceptions.ConnectionError as errc:
        #     return f"Error Connecting: {errc}"
        # except requests.exceptions.Timeout as errt:
        #     return f"Timeout Error: {errt}"
        # except requests.exceptions.RequestException as err:
        #     return f"OOps: Something Else: {err}"

        response = requests.post(complete_url, data=json.dumps(data), headers=headers)
        # response.raise_for_status()
        if response.cookies:
            self.cookies = response.cookies

        if response.status_code == 204:
            return response
        else:
            raise Exception("Something wrong with your auth, please check it out.")

    def get_tokens(self, endpoint: str = "api/user/tokens"):
        """post request"""

        complete_url = f"http://{self.ip}/cct/{endpoint}"
        headers = {"Content-Type": "application/json"}
        print(complete_url)
        # try:
        #     response = requests.post(complete_url, data=json.dumps(data), headers=headers)

        #     response.raise_for_status()
        #     return response.json()
        # except requests.exceptions.HTTPError as errh:
        #     return f"Http Error: {errh}"
        # except requests.exceptions.ConnectionError as errc:
        #     return f"Error Connecting: {errc}"
        # except requests.exceptions.Timeout as errt:
        #     return f"Timeout Error: {errt}"
        # except requests.exceptions.RequestException as err:
        #     return f"OOps: Something Else: {err}"

        response = requests.get(complete_url, headers=headers)
        # response.raise_for_status()
        return response

    def get_tasks(self, endpoint: str = "api/project/1/tasks"):
        """Get tasks from CCT"""

        complete_url = f"http://{self.ip}/cct/{endpoint}"
        headers = {"Content-Type": "application/json"}
        print(complete_url)

        response = requests.get(complete_url, headers=headers, cookies=self.cookies)
        # response.raise_for_status()
        return response

    def get_creds(self, endpoint: str = "api/project/1/keys?sort=type&order=asc"):
        """Get tasks from CCT"""

        complete_url = f"http://{self.ip}/cct/{endpoint}"
        headers = {"Content-Type": "application/json"}
        print(complete_url)
        response = requests.get(complete_url, headers=headers, cookies=self.cookies)
        # response.raise_for_status()
        return response

    def get_events(self, endpoint: str = "api/events"):
        """Get events from CCT"""
        complete_url = f"http://{self.ip}/cct/{endpoint}"
        headers = {"Content-Type": "application/json"}
        print(complete_url)
        response = requests.get(complete_url, headers=headers, cookies=self.cookies)
        # response.raise_for_status()
        return response

    def get_one_task(
        self, task_id: str = "1", endpoint: str = "api/project/1/tasks/1/output"
    ):
        """Get one task by selected task_id from CCT"""
        if endpoint != "api/project/1/tasks/1/output":
            endpoint = f"api/project/1/tasks/{task_id}/output"

        complete_url = f"http://{self.ip}/cct/{endpoint}"
        headers = {"Content-Type": "application/json"}
        print(complete_url)
        response = requests.get(complete_url, headers=headers, cookies=self.cookies)
        # response.raise_for_status()
        return response

    def get_licenses(self, endpoint: str = "api/licensing"):
        """Get events from CCT"""
        complete_url = f"http://{self.ip}/cct/{endpoint}"
        headers = {"Content-Type": "application/json"}
        print(complete_url)
        response = requests.get(complete_url, headers=headers, cookies=self.cookies)
        # response.raise_for_status()
        return response


# test_cct = CCT("104.199.135.229")
# test_cct.username = "admin"
# test_cct.password = "admin"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create fs proc and alter fs for new host ip and checkout backup info on it"
    )
    parser.add_argument("-V", "--vault", required=False, help="Vault Pass")
    parser.add_argument("-c", "--cls", required=False, help="The cluster.")
    parser.add_argument(
        "-i",
        "--ip",
        required=False,
        help="The remote IP address that you would love to check out backrest info.",
    )
    parser.add_argument(
        "-m", "--method", required=False, help="The method enum for manipulate data"
    )
    parser.add_argument(
        "-newv",
        "--new_value",
        required=False,
        type=str,
        help="The method enum for manipulate data",
    )
    parser.add_argument(
        "-db",
        "--dbname",
        required=False,
        type=str,
        help="if the method is cmdb_citus, specify the database that you are gonna use",
    )
    parser.add_argument(
        "-s",
        "--shard",
        required=False,
        type=str,
        help="if the method is add_new_shard or add_worker, specify the shard name that you are gonna use",
    )
    args = parser.parse_args()
    host = args.ip

    ava_options = [
        "bk_info",
        "add_og_db",
        "del_db",
        "add_og_cron",
        "del_cron",
        "update_cron",
        "cmdb_citus",
        "add_new_shard",
        "add_worker"
    ]

    crys = Crystal(ip="meta", is_remote=False)
    crys.conn_string()
    crys.cct_conn()

    if args.method and args.method in ava_options:
        method = args.method
        cluster_name = args.cls
        if method == "update_cron":
            print(args.new_value)
            cnt = crys.count(
                "crystaldb.group_var", f"cls='{cluster_name}' and key = 'node_crontab'"
            )
            crys.set_group(cluster_name)
            new_value = args.new_value
            if cnt == 0:
                crys.add_og_cron()
            crys.update_cron(new_value)
            crys.get_cron()
        elif method == "add_og_cron":
            crys.set_group(cluster_name)
            crys.add_og_cron()
            crys.get_cron()
        elif method == "del_cron":
            crys.set_group(cluster_name)
            crys.del_cron()
        elif method == "cmdb_citus":
            if not args.cls or not args.ip:
                # Raise the exception if cls or ip is not provided
                raise Exception(
                    "Please provide cls and ip argument for cmdb_citus method."
                )
            dbname = args.dbname if args.dbname else "test"
            crys.cmdb_citus(new_host_ip=host, cluster=cluster_name, dbname=dbname)
        elif method == "add_new_shard":
            if not args.cls or not args.ip or not args.shard or not args.dbname:
                # Raise the exception if cls or ip is not provided
                raise Exception(
                    "Please provide cls, ip, dbname and shard argument for add_new_shard method."
                )
            ip = args.ip
            shard = args.shard
            dbname = args.dbname
            crys.add_new_shard(new_host_ip=ip, cluster_name=cluster_name, shard_name=shard, dbname=dbname)
        elif method == "add_worker":
            if not args.cls or not args.ip or not args.shard:
                # Raise the exception if cls or ip is not provided
                raise Exception(
                    "Please provide cls, ip and shard argument for add_worker method."
                )
            ip = args.ip
            shard = args.shard
            crys.add_worker(shard_name=shard, cluster_name=cluster_name, new_ip=ip)
        else:
            pass
    elif args.method and args.method not in ava_options:
        raise Exception(
            "your method is not provided in avaliable options:", ava_options
        )
    else:
        crys.create_proc_fs()
        crys.bk_info_init()
        crys.alter_fs_host_options(new_host=host)
        crys.create_view_pgbackrest_info()

        result = crys.glimpse(table="crystaldb.pgbackrest_info_main")
        print(json.dumps(result[0][0][0]))
