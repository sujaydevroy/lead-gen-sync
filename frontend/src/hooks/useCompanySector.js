import { useAuth } from '@/components/providers/AuthProvider';

/** The logged-in company's sector from the API ({ sector, sub_sectors }) or null. */
export default function useCompanySector() {
  return useAuth().sectorDefinition;
}
