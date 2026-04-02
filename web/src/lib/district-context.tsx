"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getDistricts } from "@/lib/api/client";
import type { District } from "@/lib/types";

interface DistrictContextValue {
  districts: District[];
  activeDistrictId: string | null;
  setActiveDistrictId: (districtId: string) => void;
  isLoading: boolean;
}

const DistrictContext = createContext<DistrictContextValue | undefined>(undefined);

export function DistrictProvider({ children }: { children: React.ReactNode }) {
  const { data, isLoading } = useQuery({
    queryKey: ["districts"],
    queryFn: getDistricts,
  });

  const districts = data?.districts ?? [];
  const [activeDistrictId, setActiveDistrictId] = useState<string | null>(null);

  useEffect(() => {
    if (!activeDistrictId && districts.length > 0) {
      setActiveDistrictId(districts[0].district_id);
    }
  }, [activeDistrictId, districts]);

  const value = useMemo(
    () => ({
      districts,
      activeDistrictId,
      setActiveDistrictId,
      isLoading,
    }),
    [districts, activeDistrictId, isLoading],
  );

  return <DistrictContext.Provider value={value}>{children}</DistrictContext.Provider>;
}

export function useDistricts() {
  const context = useContext(DistrictContext);
  if (!context) {
    throw new Error("useDistricts must be used within DistrictProvider");
  }
  return context;
}
