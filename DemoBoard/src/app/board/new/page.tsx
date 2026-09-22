import Link from "next/link";
import { createPostAction } from "@/app/board/actions";
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

export default function NewPostPage() {
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 px-4 py-10">
      <h1 className="text-2xl font-bold tracking-tight">글쓰기</h1>

      <Card>
        <form action={createPostAction}>
          <CardHeader>
            <CardTitle className="sr-only">새 글 작성</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="title">제목</Label>
              <Input id="title" name="title" placeholder="제목을 입력하세요" required />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="author">작성자</Label>
              <Input id="author" name="author" placeholder="이름을 입력하세요" required />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="content">내용</Label>
              <Textarea
                id="content"
                name="content"
                placeholder="내용을 입력하세요"
                rows={10}
                required
              />
            </div>
          </CardContent>
          <CardFooter className="justify-end gap-2">
            <Button variant="outline" render={<Link href="/board" />}>
              취소
            </Button>
            <Button type="submit">등록</Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
