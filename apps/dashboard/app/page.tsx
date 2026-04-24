import { createClient } from "@/utils/supabase/server";
import { cookies } from "next/headers";

export default async function Page() {
  const cookieStore = await cookies();
  const supabase = createClient(cookieStore);

  const { data: todos } = await supabase.from("todos").select();

  return (
    <main>
      <h1>AutoChat Colombia</h1>
      <p>Panel admin (MVP) con Supabase.</p>
      <ul>
        {todos?.map((todo: { id: string; name: string }) => (
          <li key={todo.id}>{todo.name}</li>
        ))}
      </ul>
    </main>
  );
}
