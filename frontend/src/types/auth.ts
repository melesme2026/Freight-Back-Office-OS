export type AuthUser = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  organization_id: string;
};

export type LoginRequest = {
  organization_id?: string;
  email: string;
  password: string;
};

export type LoginResponse = {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
};