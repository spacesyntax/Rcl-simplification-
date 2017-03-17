-- object: public."createRoundaboutLinks" | type: FUNCTION --
-- DROP FUNCTION IF EXISTS public."createRoundaboutLinks"() CASCADE;
CREATE FUNCTION public."createRoundaboutLinks" ()
	RETURNS void
	LANGUAGE plpgsql
	VOLATILE
	CALLED ON NULL INPUT
	SECURITY INVOKER
	COST 1
	AS $$
DECLARE r record;
BEGIN

PERFORM pgr_createTopology('public.road', 0.001, 'geom', 'id','source','target');

TRUNCATE public.roundabout_links;

FOR r in (SELECT *
          FROM public.road
          WHERE (class = 'Unclassified' OR class = 'Not Classified') AND formofway = 'Roundabout')

  LOOP
  --IF NOT visited @> ARRAY[r.id]::bigint[]
  --THEN
  INSERT INTO public.roundabout_links (ids_roundabout, geom)
  WITH roundabout_groups AS(WITH RECURSIVE roundabout(idlist,s_t_list) AS (
                                  SELECT ARRAY[id] AS idlist, ARRAY[source]||ARRAY[target] AS s_t_list
                                    FROM (SELECT * FROM public.road WHERE (class = 'Unclassified' OR class = 'Not Classified') AND formofway = 'Roundabout') AS t
                                    WHERE  t.id =  r.id

                                    UNION ALL

                                    SELECT array_append(rb.idlist,e.id) AS idlist, rb.s_t_list||ARRAY[e.source]||ARRAY[e.target] AS s_t_list
                                    FROM (SELECT * FROM public.road WHERE (class = 'Unclassified' OR class = 'Not Classified') AND formofway = 'Roundabout') AS e,
                                         roundabout AS rb
                                    WHERE  (rb.s_t_list@> ARRAY[e.source]  OR rb.s_t_list@> ARRAY[e.target]) AND NOT rb.idlist @> ARRAY[e.id])
                              SELECT sort(b.idlist) AS idlist, uniq(sort(b.s_t_list)) AS s_t_list
                              FROM roundabout AS b
                              ORDER BY array_length(idlist, 1) DESC
                              LIMIT 1),
                    nodes AS(SELECT ST_Collect(ARRAY((SELECT the_geom AS geom FROM public.road_vertices_pgr, roundabout_groups WHERE roundabout_groups.s_t_list::bigint[] @> ARRAY[id]))) AS multi_geom),
                 centroid AS(SELECT ST_Centroid(multi_geom) AS geom FROM nodes),
           ---  line_to_link AS(SELECT DISTINCT ON (id) id, geom
               ---             FROM (SELECT * FROM public.road WHERE (class = 'Unclassified' OR class = 'Not Classified') AND NOT formofway = 'Roundabout') AS lines,
                   ---               nodes
								--- WHERE ST_Touches(lines.geom, nodes.multi_geom)),
line_to_link AS(SELECT DISTINCT ON (id) id, geom
                FROM (SELECT id,geom FROM public.road
                      WHERE (class = 'Unclassified' OR class = 'Not Classified') AND NOT formofway = 'Roundabout'
                          AND NOT id IN (SELECT ids_dual_car[1]
                                         FROM public.dual_car_links
                                         WHERE ids_dual_car[1] IS NOT NULL

                                         UNION

                                         SELECT ids_dual_car[2]
                                         FROM public.dual_car_links
                                         WHERE ids_dual_car[2] IS NOT NULL)

                      UNION

                      SELECT id,geom
                      FROM public.dual_car_links) AS lines,
                      nodes
                WHERE ST_Touches(lines.geom, nodes.multi_geom)),


                 endpoint AS(SELECT CASE WHEN ST_Intersects(ST_StartPoint(line_to_link.geom), nodes.multi_geom)  AND NOT ST_Intersects(ST_EndPoint(line_to_link.geom), nodes.multi_geom)
                                    THEN ST_StartPoint(line_to_link.geom)
                                    WHEN ST_Intersects(ST_EndPoint(line_to_link.geom), nodes.multi_geom) AND NOT ST_Intersects(ST_StartPoint(line_to_link.geom), nodes.multi_geom)
                                    THEN ST_EndPoint(line_to_link.geom)
  								  WHEN ST_Intersects(ST_StartPoint(line_to_link.geom), nodes.multi_geom) AND  ST_Intersects(ST_EndPoint(line_to_link.geom), nodes.multi_geom)
  								  THEN (ST_Dump(ST_Multi(ST_Collect(ST_StartPoint(line_to_link.geom), ST_EndPoint(line_to_link.geom))))).geom
  								  END AS geom
  								FROM line_to_link, nodes)
                  --visited AS(SELECT roundabout_groups.idlist::bigint[] INTO visited FROM  roundabout_groups)
    SELECT DISTINCT ON (endpoint.geom)  roundabout_groups.idlist::bigint[], ST_MakeLine(centroid.geom, endpoint.geom)
    FROM  roundabout_groups, endpoint, centroid, line_to_link;

  --END IF;
END LOOP;

-- Delete duplicate geometries
WITH unique_geom (dup_id, id, geom) as
(SELECT row_number() OVER (PARTITION BY ST_AsBinary(geom)) as dup_id , id, geom FROM public.roundabout_links)
DELETE FROM public.roundabout_links
WHERE id IN (SELECT id FROM unique_geom WHERE dup_id > 1);

RETURN;
END;
$$;
-- ddl-end --
ALTER FUNCTION public."createRoundaboutLinks"() OWNER TO postgres;
-- ddl-end --

