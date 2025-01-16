import slashPickUserTrigger from "./triggers/slash_pick_user.ts";
import pickUserWorkflow from "./workflows/pick_user_workflow.ts";

export default {
  // The Slack CLI uses this to discover your triggers/workflows
  triggers: [slashPickUserTrigger],
  workflows: [pickUserWorkflow],
};

console.log("Hello from Coffee Bot!");