import Link from "next/link";
import { notFound } from "next/navigation";
import { getPost, incrementViews } from "@/lib/posts";
import { deletePostAction } from "@/app/board/actions";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default async function PostDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const post = await getPost(id);

  if (!post) {
    notFound();
  }

  await incrementViews(id);

  const deleteWithId = deletePostAction.bind(null, id);

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 px-4 py-10">
      <Card>
        <CardHeader className="gap-2">
          <CardTitle className="text-xl">{post.title}</CardTitle>
          <div className="flex gap-3 text-sm text-muted-foreground">
            <span>{post.author}</span>
            <span>{formatDate(post.createdAt)}</span>
            <span>조회 {post.views}</span>
          </div>
        </CardHeader>
        <Separator />
        <CardContent className="min-h-32 whitespace-pre-wrap pt-6 text-sm leading-relaxed">
          {post.content}
        </CardContent>
        <CardFooter className="justify-between">
          <Button variant="outline" render={<Link href="/board" />}>
            목록으로
          </Button>
          <div className="flex gap-2">
            <Button variant="outline" render={<Link href={`/board/${post.id}/edit`} />}>
              수정
            </Button>
            <form action={deleteWithId}>
              <Button type="submit" variant="destructive">
                삭제
              </Button>
            </form>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}
