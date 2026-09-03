---
name: react
description: React component patterns, hooks, state management, and project structure. Use when building React UIs or reviewing frontend code.
---

# React

## Project Structure
```
src/
  components/     # reusable UI (Button, Modal, Card)
  pages/          # route-level components (HomePage, ProductPage)
  hooks/          # custom hooks (useAuth, useFetch, useForm)
  services/       # API calls (api.ts, auth.ts)
  store/          # global state (Zustand or Context)
  types/          # TypeScript interfaces
  utils/          # pure helpers
```

## Component Pattern
```tsx
// Always functional components + TypeScript
interface Props {
  title: string;
  count: number;
  onIncrement: () => void;
}

export function Counter({ title, count, onIncrement }: Props) {
  return (
    <div>
      <h2>{title}</h2>
      <p>{count}</p>
      <button onClick={onIncrement}>+</button>
    </div>
  );
}
```

## Key Hooks
```tsx
// Data fetching
const [data, setData] = useState<Product[]>([]);
const [loading, setLoading] = useState(true);

useEffect(() => {
  fetch("/api/products")
    .then(r => r.json())
    .then(d => { setData(d); setLoading(false); });
}, []);   // [] = run once on mount

// Form state
const [form, setForm] = useState({ name: "", price: "" });
const handleChange = (e: React.ChangeEvent<HTMLInputElement>) =>
  setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));

// Avoid: useEffect with missing deps, direct mutation of state
```

## Custom Hook Pattern
```tsx
// hooks/useProducts.ts
export function useProducts() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState<string | null>(null);

  useEffect(() => {
    api.getProducts()
      .then(setProducts)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return { products, loading, error };
}

// Usage
const { products, loading } = useProducts();
```

## Global State (Zustand — preferred over Redux)
```tsx
import { create } from "zustand";

interface AuthStore {
  user: User | null;
  login: (user: User) => void;
  logout: () => void;
}

export const useAuth = create<AuthStore>(set => ({
  user: null,
  login: (user) => set({ user }),
  logout: () => set({ user: null }),
}));
```

## API Service Layer
```ts
// services/api.ts
const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export const api = {
  getProducts: (): Promise<Product[]> =>
    fetch(`${BASE}/products`).then(r => r.json()),

  createProduct: (data: ProductCreate): Promise<Product> =>
    fetch(`${BASE}/products`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }).then(r => r.json()),
};
```

## Rules
- One component per file, filename = component name
- Never fetch inside a component body — use `useEffect` or a custom hook
- Use `key=` on every list item (use stable IDs, not array index)
- Prefer controlled inputs (`value` + `onChange`) over uncontrolled (`ref`)
- Run: `npm run dev` (Vite) or `npm start` (CRA)
