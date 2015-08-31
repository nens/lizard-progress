DROP VIEW IF EXISTS publiekskaart_almere;
CREATE VIEW publiekskaart_almere AS (
    SELECT
        location.id,
        location.location_code,
        CASE
            WHEN location.complete
            THEN location.timestamp
            ELSE location.planned_date
        END AS inspection_date,
        location.location_type,
        location.complete,
        location.the_geom,
        (location.planned_date IS NULL) AS not_yet_planned,
        CASE
            WHEN location.complete THEN 1
            WHEN EXTRACT(WEEK FROM location.planned_date) = EXTRACT(WEEK FROM current_date) THEN 2
            WHEN EXTRACT(WEEK FROM location.planned_date) = EXTRACT(WEEK FROM current_date) + 1 THEN 3
            ELSE 4
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
        project.organization_id = 3 -- Gemeente Almere is 3 on staging, 6 on production
        AND project.project_type_id != 11 -- on Production check id == 31 (Planmatig)
        AND NOT project.is_archived
        AND (
             (NOT location.complete AND
             location.planned_date IS NOT NULL AND
             location.planned_date >= current_date - interval '30 days')
            OR
             (location.complete AND
              location.timestamp <= current_date + interval '30 days'))
        AND location.location_type IN ('drain', 'manhole', 'pipe')
);
