-- Headless Mason tool installation for playbooks/nvim.yml.
-- Installs all listed packages via the mason-registry API, waits for every
-- installation to finish, then exits nvim with 0 (all OK) or 1 (any failed).

local tools = {
  "ansible-language-server",
  "bash-language-server",
  "black",
  "efm",
  "gofumpt",
  "goimports",
  "gopls",
  "isort",
  "lua-language-server",
  "prettierd",
  "pyright",
  "shellcheck",
  "shfmt",
  "starpls",
  "stylua",
  "yaml-language-server",
}

-- Abort if installations take longer than 10 minutes.
vim.defer_fn(function()
  io.stderr:write("mason-headless-install: timed out after 10 minutes\n")
  vim.cmd("cquit 1")
end, 600000)

local registry = require("mason-registry")

registry.refresh(function()
  local to_install = {}
  for _, name in ipairs(tools) do
    local ok, pkg = pcall(registry.get_package, name)
    if ok and not pkg:is_installed() then
      table.insert(to_install, pkg)
    end
  end

  if #to_install == 0 then
    vim.schedule(function()
      vim.cmd("qall")
    end)
    return
  end

  local done = 0
  local failed = {}

  for _, pkg in ipairs(to_install) do
    pkg:once("install:success", function()
      done = done + 1
      if done == #to_install then
        vim.schedule(function()
          if #failed > 0 then
            io.stderr:write("mason-headless-install: failed: " .. table.concat(failed, ", ") .. "\n")
            vim.cmd("cquit 1")
          else
            vim.cmd("qall")
          end
        end)
      end
    end)

    pkg:once("install:failed", function()
      table.insert(failed, pkg.name)
      done = done + 1
      if done == #to_install then
        vim.schedule(function()
          io.stderr:write("mason-headless-install: failed: " .. table.concat(failed, ", ") .. "\n")
          vim.cmd("cquit 1")
        end)
      end
    end)

    pkg:install()
  end
end)
