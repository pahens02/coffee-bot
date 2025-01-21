import { serve } from "https://deno.land/std@0.140.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js";

// Supabase credentials
const supabaseUrl = "https://pchmmpxhqramfpgomptg.supabase.co";
const supabaseKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBjaG1tcHhocXJhbWZwZ29tcHRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzY3MjU4NDIsImV4cCI6MjA1MjMwMTg0Mn0.nCCTeALYevk5k-ITK4Zbt4VYMjCDYx0jum9VfXZWq5Y"; // Use the service role key
const supabase = createClient(supabaseUrl, supabaseKey);

// Slack Webhook URL
const SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/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";

serve(async (req) => {
  try {
    // Parse the request body
    const { channel_id, brew_time } = await req.json();

    // Wait for 10 minutes
    await new Promise((resolve) => setTimeout(resolve, 10 * 60 * 1000));

    // Send follow-up message via Slack webhook
    const response = await fetch(SLACK_WEBHOOK_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: "☕ Coffee is ready!",
        channel: channel_id,
      }),
    });

    // Check for errors in the response
    if (!response.ok) {
      const errorText = await response.text();
      console.error("Slack webhook error:", errorText);
      return new Response("Failed to send message to Slack", { status: 500 });
    }

    console.log("Message sent to Slack successfully");
    return new Response("Message sent successfully", { status: 200 });
  } catch (error) {
    console.error("Error in edge function:", error);
    return new Response("Internal server error", { status: 500 });
  }
});
