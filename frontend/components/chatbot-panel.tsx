"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import GlassSurface from "@/components/GlassSurface";
import { IconChevronDown, IconSend } from "@tabler/icons-react";

const MODELS = [
  { id: "claude", name: "Claude", src: "/claude (1).svg" },
  { id: "openai", name: "OpenAI", src: "/openai.png" },
  { id: "gemini", name: "Gemini", src: "/gemini (1).png" },
  { id: "deepseek", name: "DeepSeek", src: "/deepseek (1).png" },
] as const;

type ModelId = (typeof MODELS)[number]["id"];

export function ChatbotPanel({ onSend }: { onSend?: () => void }) {
  const [selectedModel, setSelectedModel] = useState<ModelId>("claude");
  const [input, setInput] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;
    setInput("");
    onSend?.();
  };

  return (
    <aside className="w-full max-w-2xl px-4">
      <form onSubmit={handleSubmit} className="w-full">
        <GlassSurface
          width="100%"
          height="fit-content"
          borderRadius={16}
          className="overflow-hidden"
          contentClassName="!flex !flex-col !items-stretch !justify-center !p-0 !gap-0"
        >
          <div className="flex flex-col gap-3 px-4 pt-4 pb-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="How Can I Help You?"
              className="w-full bg-transparent text-sm text-black placeholder:text-black/50 outline-none md:text-base"
              aria-label="Message"
            />
            <div className="flex items-center justify-between gap-2">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-8 gap-2 rounded-lg border-black/15 bg-black/5 px-3 text-black hover:bg-black/10 hover:text-black aria-expanded:text-black data-[state=open]:text-black data-[state=open]:bg-black/10"
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={
                        MODELS.find((m) => m.id === selectedModel)?.src ??
                        MODELS[0].src
                      }
                      alt=""
                      width={20}
                      height={20}
                      className="size-5 shrink-0 rounded object-cover"
                    />
                    <span className="text-sm font-medium">
                      {MODELS.find((m) => m.id === selectedModel)?.name ??
                        MODELS[0].name}
                    </span>
                    <IconChevronDown className="size-4 shrink-0 opacity-70" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent
                  align="start"
                  className="min-w-[--radix-dropdown-menu-trigger-width] bg-white dark:bg-neutral-900"
                >
                  {MODELS.map((model) => (
                    <DropdownMenuItem
                      key={model.id}
                      onClick={() => setSelectedModel(model.id)}
                      className="flex items-center gap-2 focus:bg-black/10 focus:text-black"
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={model.src}
                        alt=""
                        width={24}
                        height={24}
                        className="size-6 shrink-0 rounded-full object-cover"
                      />
                      <span>{model.name}</span>
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
              <Button
                type="submit"
                size="icon-sm"
                className="size-8 shrink-0 rounded-lg bg-black/15 text-black hover:bg-black/25"
                disabled={!input.trim()}
                aria-label="Send"
              >
                <IconSend className="size-4 text-black stroke-[2.5]" />
              </Button>
            </div>
          </div>
        </GlassSurface>
      </form>
    </aside>
  );
}
