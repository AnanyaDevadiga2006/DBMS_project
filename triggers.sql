-- TRIGGER 1: CALCULATE CATEGORY AND TOTAL SCORE
CREATE TRIGGER IF NOT EXISTS calc_category
AFTER INSERT ON marks
FOR EACH ROW
BEGIN
    UPDATE marks
    SET 
        total_score = ((NEW.ia1 + NEW.ia2 + NEW.ia3) / 3) + NEW.assignment,
        category = CASE
            WHEN (((NEW.ia1 + NEW.ia2 + NEW.ia3) / 3) + NEW.assignment) < 20 THEN 'red'
            WHEN (((NEW.ia1 + NEW.ia2 + NEW.ia3) / 3) + NEW.assignment) < 40 THEN 'yellow'
            ELSE 'green'
        END
    WHERE mark_id = NEW.mark_id;
END;


-- TRIGGER 2: INSERT SUPPLEMENTARY WHEN MOVING INTO RED
CREATE TRIGGER IF NOT EXISTS create_supplementary
AFTER UPDATE OF category ON marks
FOR EACH ROW
WHEN NEW.category = 'red'
  AND (OLD.category IS NULL OR OLD.category <> 'red')   -- only when entering red
BEGIN
    INSERT INTO supplementary(student_id, course_code, teacher_id, reason)
    VALUES (
        NEW.student_id,
        NEW.course_code,
        (
            SELECT teacher_id
            FROM teacher
            WHERE teacher.course_code = NEW.course_code
            LIMIT 1              -- avoid "more than one row" errors
        ),
        'Low performance - supplementary required'
    );
END;


-- TRIGGER 3: REMOVE SUPPLEMENTARY WHEN LEAVING RED
CREATE TRIGGER IF NOT EXISTS remove_supplementary
AFTER UPDATE OF category ON marks
FOR EACH ROW
WHEN OLD.category = 'red'
  AND NEW.category IN ('yellow', 'green')
BEGIN
    DELETE FROM supplementary
    WHERE student_id = NEW.student_id
      AND course_code = NEW.course_code;
END;
