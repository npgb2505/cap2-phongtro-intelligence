import { ListingsExplorer } from "../components/listings-explorer";
import { fetchMapListings } from "../lib/api";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const data = await fetchMapListings();
  return <ListingsExplorer initialData={data} />;
}
