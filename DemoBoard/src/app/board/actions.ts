"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { createPost, deletePost, updatePost } from "@/lib/posts";

export async function createPostAction(formData: FormData) {
  const title = String(formData.get("title") ?? "").trim();
  const author = String(formData.get("author") ?? "").trim();
  const content = String(formData.get("content") ?? "").trim();

  if (!title || !author || !content) {
    throw new Error("제목, 작성자, 내용을 모두 입력해 주세요.");
  }

  const post = await createPost({ title, author, content });
  revalidatePath("/board");
  redirect(`/board/${post.id}`);
}

export async function updatePostAction(id: string, formData: FormData) {
  const title = String(formData.get("title") ?? "").trim();
  const author = String(formData.get("author") ?? "").trim();
  const content = String(formData.get("content") ?? "").trim();

  if (!title || !author || !content) {
    throw new Error("제목, 작성자, 내용을 모두 입력해 주세요.");
  }

  await updatePost(id, { title, author, content });
  revalidatePath("/board");
  revalidatePath(`/board/${id}`);
  redirect(`/board/${id}`);
}

export async function deletePostAction(id: string) {
  await deletePost(id);
  revalidatePath("/board");
  redirect("/board");
}
