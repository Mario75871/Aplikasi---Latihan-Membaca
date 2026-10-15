"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { StudentShell } from "@/components/student/StudentShell";
import { QuestionCard } from "@/components/student/QuestionCard";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/icons";
import { getReading, submitComprehension, ApiError } from "@/lib/api";
import type { ReadingQuestion } from "@/lib/types";

/** S-06 Jawab Pertanyaan — satu kartu per layar, opsi besar. */
function AnswerScreen() {
  const router = useRouter();
  const params = useSearchParams();
  const assessmentId = params.get("assessment");
  const readingId = params.get("reading");

  const [questions, setQuestions] = useState<ReadingQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getReading(readingId)
      .then((r) => {
        if (!active) return;
        setQuestions(r?.questions ?? []);
        setLoading(false);
      })
      .catch(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [readingId]);

  async function finish(finalAnswers: Record<string, string>) {
    if (!assessmentId) {
      router.push("/assess/done");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await submitComprehension(assessmentId, finalAnswers);
      router.push(`/assess/done?assessment=${assessmentId}`);
    } catch (e) {
      setSubmitting(false);
      setError(
        e instanceof ApiError
          ? e.detail
          : "Jawaban belum bisa dikirim. Coba lagi ya."
      );
    }
  }

  function next() {
    if (index < questions.length - 1) {
      setIndex((i) => i + 1);
    } else {
      void finish(answers);
    }
  }

  if (loading) {
    return (
      <StudentShell step={3}>
        <div className="flex flex-1 items-center justify-center px-6 pb-16">
          <p className="text-lg text-slate-500">Menyiapkan pertanyaan…</p>
        </div>
      </StudentShell>
    );
  }

  if (questions.length === 0) {
    return (
      <StudentShell step={3}>
        <div className="flex flex-1 flex-col items-center justify-center gap-6 px-6 pb-16 text-center">
          <p className="text-lg text-slate-600">
            Belum ada pertanyaan untuk bacaan ini.
          </p>
          <Button variant="primary" size="lg" onClick={() => void finish({})}>
            Lanjut
            <Icon name="arrow-right" size={20} />
          </Button>
        </div>
      </StudentShell>
    );
  }

  const q = questions[index];
  const isLast = index === questions.length - 1;

  return (
    <StudentShell step={3}>
      <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 pb-16">
        {error && (
          <p className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {error}
          </p>
        )}
        <QuestionCard
          competency={q.competency}
          question={q.prompt}
          options={q.options}
          index={index + 1}
          total={questions.length}
          value={answers[q.id]}
          onChange={(v) => setAnswers((a) => ({ ...a, [q.id]: v }))}
          onNext={next}
        />
        {isLast && submitting && (
          <p className="text-sm text-slate-500">Mengirim jawaban…</p>
        )}
      </div>
    </StudentShell>
  );
}

export default function StudentAnswerPage() {
  return (
    <Suspense
      fallback={
        <StudentShell step={3}>
          <div className="flex flex-1 items-center justify-center px-6 pb-16">
            <p className="text-lg text-slate-500">Menyiapkan pertanyaan…</p>
          </div>
        </StudentShell>
      }
    >
      <AnswerScreen />
    </Suspense>
  );
}
