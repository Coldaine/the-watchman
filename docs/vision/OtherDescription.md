# .github/dependabot.yml
version: 2

updates:
  # GitHub Actions
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "08:00"
      timezone: "UTC"
    groups:
      github-actions-minor-major:
        update-types:
          - "minor"
          - "major"

  # npm / yarn / pnpm
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "08:00"
      timezone: "UTC"
    groups:
      npm-patch:
        update-types: ["patch"]
      npm-minor-major:
        update-types: ["minor", "major"]

  # Python (pip / pipenv / poetry)
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "08:00"
      timezone: "UTC"
    groups:
      python-patch:
        update-types: ["patch"]
      python-minor-major:
        update-types: ["minor", "major"]

  # Ruby (Bundler)
  - package-ecosystem: "bundler"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "08:00"
      timezone: "UTC"
    groups:
      ruby-patch:
        update-types: ["patch"]
      ruby-minor-major:
        update-types: ["minor", "major"]

  # Go modules
  - package-ecosystem: "gomod"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "08:00"
      timezone: "UTC"
    groups:
      go-patch:
        update-types: ["patch"]
      go-minor-major:
        update-types: ["minor", "major"]

  # Docker
  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "08:00"
      timezone: "UTC"
    # Docker doesn't use SemVer consistently, so we group all updates
    groups:
      docker-all:
        patterns: ["*"]

  # Terraform
  - package-ecosystem: "terraform"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "08:00"
      timezone: "UTC"
    groups:
      terraform-all:
        patterns: ["*"]
