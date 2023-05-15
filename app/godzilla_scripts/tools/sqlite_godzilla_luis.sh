~/sqlite3 /mnt/HD/HD_a2/restsdk-data/data/db/index.db <<END_SQL

SELECT COUNT(*) FROM Files WHERE parentID IS NOT null;

END_SQL
