import "server-only";
import { supabase } from "@/lib/supabase/server";

export interface Post {
  id: string;
  title: string;
  author: string;
  content: string;
  createdAt: string;
  views: number;
}

interface PostRow {
  id: string;
  title: string;
  author: string;
  content: string;
  created_at: string;
  views: number;
}

function toPost(row: PostRow): Post {
  return {
    id: row.id,
    title: row.title,
    author: row.author,
    content: row.content,
    createdAt: row.created_at,
    views: row.views,
  };
}

export async function getPosts(): Promise<Post[]> {
  const { data, error } = await supabase
    .from("posts")
    .select("*")
    .order("created_at", { ascending: false });

  if (error) throw new Error(error.message);
  return (data as PostRow[]).map(toPost);
}

export async function getPost(id: string): Promise<Post | undefined> {
  const { data, error } = await supabase
    .from("posts")
    .select("*")
    .eq("id", id)
    .maybeSingle();

  if (error) throw new Error(error.message);
  return data ? toPost(data as PostRow) : undefined;
}

export async function incrementViews(id: string): Promise<void> {
  const { error } = await supabase.rpc("increment_post_views", {
    post_id: id,
  });
  if (error) throw new Error(error.message);
}

export async function createPost(input: {
  title: string;
  author: string;
  content: string;
}): Promise<Post> {
  const { data, error } = await supabase
    .from("posts")
    .insert(input)
    .select()
    .single();

  if (error) throw new Error(error.message);
  return toPost(data as PostRow);
}

export async function updatePost(
  id: string,
  input: { title: string; author: string; content: string }
): Promise<void> {
  const { error } = await supabase.from("posts").update(input).eq("id", id);
  if (error) throw new Error(error.message);
}

export async function deletePost(id: string): Promise<void> {
  const { error } = await supabase.from("posts").delete().eq("id", id);
  if (error) throw new Error(error.message);
}
