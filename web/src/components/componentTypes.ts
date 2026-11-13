export type StatusTone = "NEUTRAL" | "OK" | "WARN" | "DANGER" | "INFO";
export interface TableColumn {
  readonly key: string;
  readonly label: string;
  readonly sortable?: boolean | undefined;
  readonly mono?: boolean | undefined;
}
export type TableRow = Record<string, string | number | null>;
