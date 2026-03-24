export type Driver = {
  id: string;
  full_name: string;
  phone?: string | null;
  email?: string | null;
  is_active: boolean;

  customer_account_id?: string | null;
  organization_id?: string | null;

  created_at?: string | null;
  updated_at?: string | null;
};