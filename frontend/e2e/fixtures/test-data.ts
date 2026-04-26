export const seed = {
  organizationId: "org-e2e-001",
  owner: {
    email: "owner.e2e@example.com",
    password: "Password123!",
    role: "owner",
  },
  driver: {
    id: "drv-e2e-001",
    email: "driver.e2e@example.com",
    password: "Password123!",
    name: "Driver E2E",
    role: "driver",
  },
  broker: {
    id: "brk-e2e-001",
    name: "Broker E2E",
    email: "broker@example.com",
  },
  customer: {
    id: "cust-e2e-001",
    account_name: "Customer E2E",
  },
  load: {
    id: "load-e2e-001",
    load_number: `LD-E2E-${Date.now()}`,
    pickup_location: "Dallas, TX",
    delivery_location: "Austin, TX",
  },
};
