-- functions that are used to speed up important parts of mediaTUM.
-- they could all be implemented in Python instead but this is faster ;)

-- Finds all paths to `node_id` that are accessible with the given access params `group_ids`, `ipaddr` and `date`.
-- Node IDs matching `exclude_container_ids` won't be returned.
-- Typically, `node_id` will be an id of a content node that is contained in one or more containers.
CREATE OR REPLACE FUNCTION accessible_container_paths(node_id integer, exclude_container_ids integer[]=ARRAY[]::integer[]
                                                     ,group_ids integer[]=NULL, ipaddr inet=NULL, date date=NULL)
    RETURNS setof integer[]
    LANGUAGE plpgsql
    SET search_path = :search_path
    IMMUTABLE
    AS $f$
BEGIN
RETURN QUERY SELECT 
    array_append(array_agg(q.nid), nm.nid) as path

    FROM nodemapping nm,
    LATERAL (
        SELECT nid, has_read_access_to_node(nid, group_ids, ipaddr, date) as accessible
        FROM noderelation nr
        WHERE nr.cid=nm.nid
        AND NOT ARRAY[nr.nid] <@ exclude_container_ids
        ORDER BY distance DESC
    ) q
    WHERE cid=node_id 
    AND has_read_access_to_node(nm.nid, group_ids, ipaddr, date)
    AND q.accessible = true
    GROUP BY nm.nid;
END;
$f$;
