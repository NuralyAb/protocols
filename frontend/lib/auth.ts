'use client';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { api, setAuthToken } from './api';

type User = { id: string; email: string; full_name: string | null; is_superuser: boolean };

type AuthState = {
  token: string | null;
  user: User | null;
  hydrated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
  fetchMe: () => Promise<void>;
};

export const useAuth = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      hydrated: false,
      login: async (email, password) => {
        const { data } = await api.post('/api/v1/auth/login', { email, password });
        setAuthToken(data.access_token);
        set({ token: data.access_token });
        await get().fetchMe();
      },
      register: async (email, password, fullName) => {
        await api.post('/api/v1/auth/register', {
          email,
          password,
          full_name: fullName || null,
        });
        await get().login(email, password);
      },
      logout: () => {
        setAuthToken(null);
        set({ token: null, user: null });
      },
      fetchMe: async () => {
        const { data } = await api.get('/api/v1/auth/me');
        set({ user: data });
      },
    }),
    {
      name: 'protocol-ai-auth',
      onRehydrateStorage: () => (state) => {
        if (state?.token) setAuthToken(state.token);
        state && (state.hydrated = true);
      },
    }
  )
);
