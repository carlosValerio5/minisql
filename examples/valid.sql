CREATE TABLE users ( id INT, active BOOL );
INSERT INTO users VALUES ( 1, true );
INSERT INTO users VALUES ( 2, false );
SELECT id, active FROM users WHERE active = true;
SELECT id + 1, NOT active FROM users WHERE id > 0;
INSERT INTO users VALUES (0, true);
SELECT id + 1, NOT active FROM users WHERE id > 0;