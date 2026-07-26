import { type ValidationResponse, getValidation } from "@/lib/api";
import { ValidationShell } from "./ValidationShell";

export const metadata = {
  title: "How We Validate — Goldeneye",
};

export default async function ValidationPage() {
  let initialData: ValidationResponse | null = null;
  try {
    initialData = await getValidation();
  } catch {
    // Client refetches; the shell renders a skeleton meanwhile.
  }
  return (
    <div className="flex h-full flex-col">
      <ValidationShell initialData={initialData} />
    </div>
  );
}
