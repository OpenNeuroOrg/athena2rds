import os
import pandas as pd
from pyathena import connect
from pyathena.pandas_cursor import PandasCursor
from sqlalchemy import event, create_engine

cursor = connect(aws_access_key_id=os.environ['AWS_KEY'],
                 aws_secret_access_key=os.environ['AWS_SECRET'],
                 s3_staging_dir='s3://aws-athena-query-results-109587625339-us-east-1/',
                 region_name='us-east-1',
                 cursor_class=PandasCursor).cursor()

# RequestDateTime column is not indexed to querying only the recent
# entries does not yield performance or cost improvements
get_all_query = """
SELECT client,
       remoteip,
       sum(bytessent)/(1024.0*1024.0*1024.0) AS downloads_gb,
       yearmonth
FROM 
    (SELECT replace(split_part(useragent,
         '/',1), '"') AS client, remoteip, bytessent, date_format(parse_datetime(RequestDateTime,'dd/MMM/yyyy:HH:mm:ss Z'), '%Y%m01') AS yearmonth
    FROM openneuro_access_logs_db.updated_access_logs_format
    WHERE STRPOS(useragent, '/') != 0
            AND bytessent > 0
            AND (httpstatus = '200'
            OR httpstatus = '206'))
GROUP BY  client, remoteip, yearmonth
"""
df = cursor.execute(get_all_query).as_pandas()

engine = create_engine(os.environ['RDS_JDBC'])
conn = engine.connect()
df.to_sql(con=engine, name='s3_logs_monthly', if_exists='replace', index=False, method='multi')
conn.close()

print('finished')
