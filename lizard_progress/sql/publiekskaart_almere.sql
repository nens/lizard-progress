CREATE VIEW publiekskaart_almere AS (
    SELECT
        location.location_code,
        location.planned_date,
        location.location_type,
        location.complete,
        location.the_geom,
        (location.planned_date IS NULL) AS not_yet_planned
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
        project.organization_id = 6 -- Gemeente Almere
        AND project.project_type_id = 31 -- Planmatig
        AND NOT project.is_archived
        AND (location.planned_date IS NULL OR
            location.planned_date >= current_date - interval '30 days')
        AND location.location_type IN ('drain', 'manhole', 'pipe')
);
