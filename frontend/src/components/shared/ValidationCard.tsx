import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SessionDocument } from "@/types/api";

type Props = {
  data: SessionDocument["validation"] | null |undefined;
};

export function ValidationCard({ data }: Props) {
  if (!data) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>✓ Validation</CardTitle>
      </CardHeader>

      <CardContent className="space-y-6">

        <Field
          label="Target Geography"
          value={data.target_geography}
        />

        <Field
          label="Industry Sector"
          value={data.industry_sector}
        />

        <div>
          <h4 className="font-semibold mb-3">
            Checked Assumptions
          </h4>

          <div className="space-y-5">
            {data.checked_assumptions.map((item, index) => (
              <div
                key={index}
                className="rounded-lg border p-4"
              >
                <div className="flex items-center justify-between mb-3">

                  <h5 className="font-semibold">
                    {item.assumption}
                  </h5>

                  <span
                    className={`rounded-full px-3 py-1 text-xs font-semibold ${
                      item.verdict === "CONFIRMED"
                        ? "bg-green-100 text-green-700"
                        : item.verdict === "PARTIAL"
                        ? "bg-yellow-100 text-yellow-700"
                        : "bg-red-100 text-red-700"
                    }`}
                  >
                    {item.verdict}
                  </span>
                </div>

                <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                  {item.evidence}
                </p>
              </div>
            ))}
          </div>
        </div>

        <Field
          label="Competitor Landscape"
          value={data.competitor_landscape}
        />

        <Field
          label="Market Notes"
          value={data.market_notes}
        />

        <div className="rounded-lg bg-secondary/10 border border-secondary/20 p-4">

          <h4 className="font-semibold mb-2">
            Validation Summary
          </h4>

          <span
            className={`inline-flex rounded-full px-3 py-1 text-sm font-semibold ${
              data.validation_summary === "STRONG"
                ? "bg-green-100 text-green-700"
                : data.validation_summary === "MODERATE"
                ? "bg-yellow-100 text-yellow-700"
                : "bg-red-100 text-red-700"
            }`}
          >
            {data.validation_summary}
          </span>

        </div>

      </CardContent>
    </Card>
  );
}

function Field({
  label,
  value,
}: {
  label: string;
  value?: string | null;
}) {
  return (
    <div className="border-b pb-3">
      <h4 className="font-semibold">
        {label}
      </h4>

      <p className="mt-1 whitespace-pre-wrap text-muted-foreground">
        {value || "-"}
      </p>
    </div>
  );
}