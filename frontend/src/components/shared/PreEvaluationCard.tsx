import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SessionDocument } from "@/types/api";

type Props = {
  data: SessionDocument["preeval"] | null | undefined;
};

export function PreEvaluationCard({ data }: Props) {
  if (!data) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>✓ Pre-Evaluation</CardTitle>
      </CardHeader>

      <CardContent className="space-y-6">

        <Field
          label="Problem Statement"
          value={data.problem_statement}
        />

        <Field
          label="Customer Segment"
          value={data.customer_segment}
        />

        <Field
          label="Consequence"
          value={data.consequence}
        />

        <Field
          label="Proposed Solution"
          value={data.proposed_solution}
        />

        <Field
          label="Target Geography"
          value={data.target_geography}
        />

        <Field
          label="Industry Sector"
          value={data.industry_sector}
        />

        <div>
          <h4 className="font-semibold mb-2">
            Assumptions
          </h4>

          <ul className="list-disc pl-5 space-y-2 text-muted-foreground">
            {data.assumptions.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
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

      <p className="mt-1 text-muted-foreground whitespace-pre-wrap">
        {value || "-"}
      </p>
    </div>
  );
}