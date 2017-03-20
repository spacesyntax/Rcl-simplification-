-- object: public."createDualCarLinks" | type: FUNCTION --
-- DROP FUNCTION IF EXISTS public."createDualCarLinks"() CASCADE;
CREATE FUNCTION public."createDualCarLinks" ()
	RETURNS void
	LANGUAGE plpgsql
	VOLATILE
	CALLED ON NULL INPUT
	SECURITY INVOKER
	COST 1
	AS $$
BEGIN

WITH dual_car AS (SELECT id, geom
                  FROM public.road
                  WHERE formofway = 'Dual Carriageway' AND (class = 'Not Classified' OR class ='Unclassified')),
  roundabouts AS (SELECT id, geom
                  FROM public.road
                  WHERE formofway = 'Roundabout' AND (class = 'Not Classified' OR class ='Unclassified')),
        links AS (INSERT INTO public.dual_car_links (ids_dual_car, geom)
                  SELECT DISTINCT ON (ST_MakeLine(ST_Intersection(d1.geom,d2.geom), ST_Line_Interpolate_point(r.geom,0.5))) ARRAY[d1.id, d2.id, r.id]::bigint[], ST_MakeLine(ST_Intersection(d1.geom,d2.geom), ST_Line_Interpolate_point(r.geom,0.5))
                  FROM dual_car AS d1, dual_car AS d2, roundabouts AS r
                  WHERE ST_Intersects(d1.geom, d2.geom) AND d1.id<>d2.id AND ST_Intersects(d1.geom, r.geom) AND ST_Intersects(d2.geom, r.geom)

                  RETURNING ids_dual_car),
new_roundabouts AS(INSERT INTO public.road(street_number, street_name, class, identifier, formofway, geom)
                  SELECT street_number, street_name, class, identifier, formofway, ST_Line_Substring(roads.geom,0,0.5)
                  FROM public.road AS roads, links
                  WHERE roads.id = ids_dual_car[3]
                  UNION
                  SELECT street_number, street_name, class, identifier, formofway, ST_Line_Substring(roads.geom,0.5,1)
                  FROM public.road AS roads, links
                  WHERE roads.id = ids_dual_car[3]),
        pairs AS (SELECT ids_dual_car[1] AS id_del
                  FROM links
                  UNION
                  SELECT ids_dual_car[2] AS id_del
                  FROM links
                  UNION
                  SELECT ids_dual_car[3] AS id_del
                  FROM links
                  )
DELETE FROM public.road
USING pairs
WHERE id = pairs.id_del;


------------------------------------------------------------------------------------
-- collapse single carriageways that are connected to a roundabout into a single line
WITH single_car AS (SELECT id, geom
                    FROM public.road
                    WHERE formofway = 'Single Carriageway' AND (class = 'Not Classified' OR class ='Unclassified')),
   roundabouts AS (SELECT id, geom
                   FROM public.road
                   WHERE formofway = 'Roundabout' AND (class = 'Not Classified' OR class ='Unclassified')),
         links AS (INSERT INTO public.dual_car_links (ids_dual_car, geom)
                  SELECT DISTINCT ON (ST_MakeLine(ST_Intersection(d1.geom,d2.geom), ST_Line_Interpolate_point(r.geom,0.5)))  ARRAY[d1.id, d2.id, r.id]::bigint[], ST_MakeLine(ST_Intersection(d1.geom,d2.geom), ST_Line_Interpolate_point(r.geom,0.5))
                  FROM single_car AS d1, single_car AS d2, roundabouts AS r
                  WHERE ST_Intersects(d1.geom, d2.geom) AND d1.id<>d2.id AND ST_Intersects(d1.geom, r.geom) AND ST_Intersects(d2.geom, r.geom)

                  RETURNING ids_dual_car),
new_roundabouts AS(INSERT INTO public.road(street_number, street_name, class, identifier, formofway, geom)
                  SELECT street_number, street_name, class, identifier, formofway, ST_Line_Substring(roads.geom,0,0.5)
                  FROM public.road AS roads, links
                  WHERE roads.id = ids_dual_car[3]
                  UNION
                  SELECT street_number, street_name, class, identifier, formofway, ST_Line_Substring(roads.geom,0.5,1)
                  FROM public.road AS roads, links
                  WHERE roads.id = ids_dual_car[3]),
        pairs AS (SELECT ids_dual_car[1] AS id_del
                  FROM links
                  UNION
                  SELECT ids_dual_car[2] AS id_del
                  FROM links
                  UNION
                  SELECT ids_dual_car[3] AS id_del
                  FROM links)
DELETE FROM public.road
USING pairs
WHERE id= pairs.id_del;


------------------------------------------------------------------------------------
-- collapse single carriageways that are connected to a roundabout into a single line
WITH single_car AS (SELECT id, geom
                    FROM public.road
                    WHERE formofway = 'Single Carriageway' AND (class = 'Not Classified' OR class ='Unclassified')),
   roundabouts AS (SELECT id, geom
                   FROM public.road
                   WHERE formofway = 'Roundabout' AND (class = 'Not Classified' OR class ='Unclassified')),
         links AS (INSERT INTO public.dual_car_links (ids_dual_car, geom)

                  SELECT DISTINCT ON (ARRAY[d.geom,r.geom])  ARRAY[d.id, r.id]::bigint[], ST_MakeLine(ST_Line_Interpolate_point(d.geom, 0.5), ST_Line_Interpolate_point(r.geom,  0.5))
                  FROM single_car AS d, roundabouts AS r
                  WHERE ST_Intersects(d.geom, r.geom) AND ST_NumGeometries(ST_Intersection(d.geom, r.geom)) > 1 AND d.id<>r.id

                  RETURNING ids_dual_car),
new_roundabouts AS(INSERT INTO public.road(street_number, street_name, class, identifier, formofway, geom)
                  SELECT street_number, street_name, class, identifier, formofway, ST_Line_Substring(roads.geom,0,0.5)
                  FROM public.road AS roads, links
                  WHERE roads.id = ids_dual_car[2]
                  UNION
                  SELECT street_number, street_name, class, identifier, formofway, ST_Line_Substring(roads.geom,0.5,1)
                  FROM public.road AS roads, links
                  WHERE roads.id = ids_dual_car[2]),
        pairs AS (SELECT ids_dual_car[1] AS id_del
                  FROM links
                  UNION
                  SELECT ids_dual_car[2] AS id_del
                  FROM links)

DELETE FROM public.road
USING pairs
WHERE id= pairs.id_del;

RETURN;
END

$$;
-- ddl-end --
ALTER FUNCTION public."createDualCarLinks"() OWNER TO postgres;
-- ddl-end --

