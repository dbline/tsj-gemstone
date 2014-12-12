DROP VIEW IF EXISTS tsj_gemstone_cutview;
CREATE VIEW tsj_gemstone_cutview AS
    WITH central AS (
        SELECT
            cut.id,
            cut.name,
            cut.abbr,
            cut.aliases,
            cut.desc,
            cut.order,
            false AS is_local
        FROM tsj_gemstone_central_cut cut
    ),
    local AS (
        SELECT
            cut.id,
            cut.name,
            cut.abbr,
            cut.aliases,
            cut.desc,
            cut.order,
            true AS is_local
        FROM tsj_gemstone_cut cut
    )

    /* Only show local cuts which aren't present in the central table */
    SELECT * FROM central
    UNION ALL
    SELECT * FROM local
    WHERE NOT EXISTS (SELECT 1 FROM central WHERE id=local.id)
;
