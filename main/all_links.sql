DROP PROCEDURE IF EXISTS all_links;
DELIMITER $$
CREATE PROCEDURE all_links()

BEGIN

START TRANSACTION;
  DROP TABLE IF EXISTS text_fields;
  DROP TABLE IF EXISTS select_cmds;

  -- 1. Create a table to store all the text fields
  CREATE TEMPORARY TABLE text_fields (
    table_name varchar(255) NOT NULL,
    column_name varchar(255) NOT NULL
  );

  CREATE TEMPORARY TABLE select_cmds (
    cmd varchar(255)
  );


  INSERT INTO text_fields
  SELECT table_name, column_name
  FROM information_schema.columns
  WHERE table_schema = 'saigatours'
  AND data_type = 'longtext'
  AND table_name not like 'main_historical%'
  AND table_name like 'main_%';

  SET @a_tag_regexp = '<a[^>]*>';

  WHILE ((SELECT COUNT(*) FROM text_fields) > 0) DO
    SET @table_name = (SELECT table_name FROM text_fields LIMIT 1);

    SET @where_clause = (SELECT group_concat(
      CONCAT(' ', column_name, ' REGEXP ''<a[^>]*>''')
      SEPARATOR ' OR'
    ) FROM text_fields WHERE table_name = @table_name);

    SET @select_cmd = CONCAT('SELECT * FROM', @table_name, @where_clause);

    INSERT INTO select_cmds
    SELECT DISTINCT CONCAT('SELECT * FROM ', table_name, ' WHERE', @where_clause)
    FROM text_fields
    WHERE table_name = @table_name;

    DELETE FROM text_fields WHERE table_name = @table_name;
  END WHILE;

  SELECT * FROM select_cmds;

  WHILE ((SELECT COUNT(*) FROM select_cmds) > 0) DO
    SET @select_cmd = (SELECT cmd FROM select_cmds LIMIT 1);

    PREPARE stmt FROM @select_cmd;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;

    DELETE FROM select_cmds WHERE cmd = @select_cmd;
  END WHILE;

  DROP TABLE text_fields;
  DROP TABLE select_cmds;

COMMIT;

END$$

DELIMITER ;

call all_links();
