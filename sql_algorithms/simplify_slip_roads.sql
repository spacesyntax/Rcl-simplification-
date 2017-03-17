-- object: public."simplifySlipRoads" | type: FUNCTION --
-- DROP FUNCTION IF EXISTS public."simplifySlipRoads"() CASCADE;
CREATE FUNCTION public."simplifySlipRoads" ()
	RETURNS void
	LANGUAGE plpgsql
	VOLATILE
	CALLED ON NULL INPUT
	SECURITY INVOKER
	COST 1
	AS $$
BEGIN

WITH slip_roads AS (SELECT id, source, target, geom
    								FROM public.road
    								WHERE (class='Unclassified' OR class = 'Not Classified') AND formofway = 'Slip Road'),
      con_Lines AS (SELECT sr.id AS slip_road, sr.geom AS slip_road_geom, r.id AS con_line, r.geom AS con_line_geom
          					FROM public.road AS r, slip_roads AS sr
          					WHERE (r.class='Unclassified' OR r.class = 'Not Classified') AND NOT r.formofway = 'Slip Road'
      								    AND (sr.source = r.source OR sr.target = r.source OR sr.target = r.target OR sr.source = r.target) AND r.id <> sr.id),
       all_pairs AS (SELECT array_agg(slip_road)::int[] AS pairs, array_agg(slip_road_geom)::geometry[] || ARRAY[con_line_geom]:: geometry[] AS geoms, con_line
          					FROM con_lines
          					GROUP BY con_line, con_line_geom),
        diamonds AS (SELECT *, ST_LineMerge(ST_Collect(geoms)), ST_MakeLine(ST_StartPoint(ST_LineMerge(ST_Collect(geoms))), ST_EndPoint(ST_LineMerge(ST_Collect(geoms)))) AS geom
                     FROM all_pairs AS alp
                     WHERE array_length(alp.pairs, 1) = 2 AND NOT ST_Equals(ST_Intersection(geoms[1], geoms[3]) , ST_Intersection(geoms[2], geoms[3]))
                         AND NOT ST_IsClosed(ST_LineMerge(ST_Collect(geoms))) AND ST_Length(geoms[3])<100
                         AND  ST_NumGeometries(ST_Intersection(ST_MakeLine(ST_StartPoint(ST_LineMerge(ST_Collect(geoms))), ST_EndPoint(ST_LineMerge(ST_Collect(geoms)))), ST_Collect(geoms)))<>2),
slip_roads_to_del AS (SELECT diamonds.pairs[1] AS id
                     FROM diamonds
                     UNION
                     SELECT diamonds.pairs[2] AS id
                     FROM diamonds),
  del_slip_roads AS (DELETE FROM public.network AS n
                    USING slip_roads_to_del AS sl
                    where n.id_road = sl.id),
    intersection AS(SELECT d.geom AS diamond, ST_Line_Locate_Point(d.geom,ST_Intersection(n.geom, d.geom)) AS fraction
                    FROM public.network AS n, diamonds AS d, slip_roads_to_del
                    WHERE ST_Crosses(n.geom, d.geom) AND n.id_road NOT IN (SELECT slip_roads_to_del.id FROM slip_roads_to_del))


INSERT INTO public.network  (class, geom)
SELECT DISTINCT ON (fraction) 'diamond link', ST_Line_Substring(i.diamond,0, i.fraction)
FROM intersection AS i

UNION

SELECT DISTINCT ON (fraction) 'diamond link', ST_Line_Substring(i.diamond, i.fraction, 1)
FROM intersection AS i ;



RETURN;
END;

$$;
-- ddl-end --
ALTER FUNCTION public."simplifySlipRoads"() OWNER TO postgres;
-- ddl-end --

