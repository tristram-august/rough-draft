import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchInjuries, type InjuryRow } from "../lib/injuries";

/** Shared query key so the drawer and the fantasy board dedupe this fetch in one session. */
export function useInjuries() {
  const query = useQuery({
    queryKey: ["injuries"],
    queryFn: fetchInjuries,
    staleTime: 5 * 60_000,
  });

  const byGsisId = React.useMemo(() => {
    const map = new Map<string, InjuryRow>();
    for (const row of query.data ?? []) map.set(row.gsis_id, row);
    return map;
  }, [query.data]);

  return { ...query, byGsisId };
}
