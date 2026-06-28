export type PaginationMeta = {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
};

export type AuthUser = {
  id: string;
  role: string;
  email?: string | null;
  phone?: string | null;
  sessionId?: string;
};
