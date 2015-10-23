DROP VIEW IF EXISTS publiekskaart_almere;
CREATE VIEW publiekskaart_almere AS (
    SELECT
        location.id,
        location.location_code,
        CASE
            WHEN location.one_measurement_uploaded
            THEN location.timestamp
            ELSE location.planned_date
        END AS inspection_date,
        location.location_type,
        location.one_measurement_uploaded,
        location.the_geom,
        CASE
            WHEN location.one_measurement_uploaded THEN 1 -- Done
            WHEN location.planned_date IS NULL THEN 0 -- Not planned
            WHEN current_date + interval '1 day' <= location.planned_date THEN 2  -- Today or tomorrow
            WHEN current_date + interval '2 days' <= location.planned_date THEN 3 -- In 2 days
            WHEN current_date + interval '3 days' <= location.planned_date THEN 4 -- Within 7 days
            ELSE 5 -- further in the future
            -- The below are for week numbers
            --           WHEN EXTRACT(WEEK FROM location.planned_date) = EXTRACT(WEEK FROM current_date) THEN 2
            --            WHEN EXTRACT(WEEK FROM location.planned_date) = EXTRACT(WEEK FROM current_date) + 1 THEN 3
        END AS color_code
    FROM
        lizard_progress_location location
    INNER JOIN
        lizard_progress_activity activity
    ON
        location.activity_id = activity.id
    INNER JOIN
        lizard_progress_project project
    ON
        activity.project_id = project.id
    WHERE
        project.organization_id = 6 -- Gemeente Almere is 3 on staging, 6 on production
        AND project.project_type_id = 31 -- on Production check id = 31 (Planmatig)
        AND NOT project.is_archived
        AND (
             (NOT location.one_measurement_uploaded AND
             location.planned_date IS NOT NULL AND
             location.planned_date >= current_date - interval '30 days')
            OR
             (location.one_measurement_uploaded AND
              location.timestamp <= current_date + interval '30 days'))
        AND location.location_type IN ('drain', 'manhole', 'pipe')
);
