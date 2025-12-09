-- VimMentor - AI-powered Vim learning assistant
return {
  -- Load from local development directory
  dir = vim.fn.expand("$HOME/code/vim-mentor"),

  -- Required dependency
  dependencies = {
    "nvim-lua/plenary.nvim",
  },

  -- Lazy load on command or keymap
  cmd = {
    "VimMentor",
    "VimMentorAsk",
    "VimMentorHistory",
    "VimMentorBookmarks",
    "VimMentorSearch",
    "VimMentorSetProvider",
    "VimMentorSetDifficulty",
  },

  keys = {
    { "<leader>vm", "<Plug>(VimMentorAsk)", desc = "VimMentor: Ask" },
    { "<leader>vh", "<cmd>VimMentorHistory<cr>", desc = "VimMentor: History" },
    { "<leader>vb", "<cmd>VimMentorBookmarks<cr>", desc = "VimMentor: Bookmarks" },
  },

  -- Configuration
  config = function()
    require("vim-mentor").setup({
      -- LLM provider auto-detected from available API keys!
      -- Will use: OPENAI_API_KEY → ANTHROPIC_API_KEY → DEEPSEEK_API_KEY
      -- Or manually specify: llm_provider = "openai",

      -- Set your skill level
      difficulty_level = "beginner", -- or "intermediate" or "advanced"

      -- Optional: Adjust timeout if needed
      timeout = 10000, -- 10 seconds

      -- Optional: Customize window appearance
      window = {
        width = 0.85,
        height = 0.85,
        border = "rounded",
      },
    })
  end,
}
