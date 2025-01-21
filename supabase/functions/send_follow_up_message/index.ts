import { serve } from "https://deno.land/std@0.140.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js";

const supabaseUrl = "https://pchmmpxhqramfpgomptg.supabase.co";
const supabaseKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBjaG1tcHhocXJhbWZwZ29tcHRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzY3MjU4NDIsImV4cCI6MjA1MjMwMTg0Mn0.nCCTeALYevk5k-ITK4Zbt4VYMjCDYx0jum9VfXZWq5Y"; // Replace with your service role key
const supabase = createClient(supabaseUrl, supabaseKey);

serve(async () => {
  const { data: jobs, error } = await supabase
    .from("brewing_jobs")
    .select("*")
    .lte("schedule_at", new Date().toISOString());

  if (error) {
    console.error("Error fetching jobs:", error);
    return new Response(JSON.stringify({ success: false, error: error.message }), { status: 500 });
  }

  for (const job of jobs) {
    const response = await fetch("https://slack.com/api/chat.postMessage", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${job.slackBotToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        channel: job.channel,
        text: "Coffee is ready!",
      }),
    });

    const result = await response.json();

    if (result.ok) {
      // Delete the processed job
      await supabase.from("brewing_jobs").delete().eq("id", job.id);
    } else {
      console.error("Error sending Slack message:", result.error);
    }
  }

  return new Response(JSON.stringify({ success: true }), { status: 200 });
});
