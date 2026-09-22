import Link from "next/link";
import { notFound } from "next/navigation";
import { getPost } from "@/lib/posts";
import { updatePostAction } from "@/app/board/actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default async function EditPostPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const post = await getPost(id);

  if (!post) {
    notFound();
  }

  const updateWithId = updatePostAction.bind(null, id);

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 px-4 py-10">
      <h1 className="text-2xl font-bold tracking-tight">글 수정</h1>

      <Card>
        <form action={updateWithId}>
          <CardHeader>
            <CardTitle className="sr-only">글 수정</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="title">제목</Label>
              <Input id="title" name="title" defaultValue={post.title} required />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="author">작성자</Label>
              <Input id="author" name="author" defaultValue={post.author} required />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="content">내용</Label>
              <Textarea
                id="content"
                name="content"
                defaultValue={post.content}
                rows={10}
                required
              />
            </div>
          </CardContent>
          <CardFooter className="justify-end gap-2">
            <Button variant="outline" render={<Link href={`/board/${post.id}`} />}>
              취소
            </Button>
            <Button type="submit">저장</Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
