export type CustomerAccountStatus =
  | "prospect"
  | "active"
  | "inactive"
  | "suspended";

export type CustomerAccount = {
  id: string;
  account_name: string;
  account_code?: string | null;
  status: CustomerAccountStatus;

  primary_contact_name?: string | null;
  primary_contact_email?: string | null;
  primary_contact_phone?: string | null;
  billing_email?: string | null;

  notes?: string | null;

  organization_id?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};