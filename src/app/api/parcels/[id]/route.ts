import { NextResponse } from "next/server";
import { getParcelProvider } from "@/lib/data/adapters";

export async function GET(_request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  try {
    const parcel = await getParcelProvider().getParcel(id);
    if (!parcel) {
      return NextResponse.json({ error: "Parcel not found" }, { status: 404 });
    }
    return NextResponse.json(parcel);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unable to load parcel" },
      { status: 500 },
    );
  }
}
