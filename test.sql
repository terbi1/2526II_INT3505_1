SELECT * FROM book
WHERE id >= %cursor
ORDER BY id ASC
LIMIT %limit

