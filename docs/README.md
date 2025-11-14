# Serger Documentation

This directory contains Jekyll-based documentation for the Serger project.

## Building the Documentation

### Prerequisites

- Ruby (2.7 or higher)
- Bundler gem

### Setup

1. Install Jekyll and dependencies:

```bash
cd docs
bundle install
```

2. Serve the documentation locally:

```bash
bundle exec jekyll serve
```

The documentation will be available at `http://localhost:4000/serger/`

### Build for Production

```bash
bundle exec jekyll build
```

The built site will be in the `_site/` directory.

## Documentation Structure

- `index.md` - Main landing page
- `getting-started.md` - Installation and quick start guide
- `configuration.md` - Configuration file format and options
- `cli-reference.md` - Complete CLI reference
- `api.md` - Programmatic API documentation
- `examples.md` - Real-world usage examples
- `_config.yml` - Jekyll configuration

## GitHub Pages Deployment

This documentation is configured for GitHub Pages. To deploy:

### Option 1: Automatic via GitHub Actions (Recommended)

A GitHub Actions workflow will automatically build and deploy the docs when changes are pushed to the main branch. The workflow is configured to:
- Build the Jekyll site from the `docs/` directory
- Deploy to GitHub Pages
- Use the `github-pages` gem for compatibility

### Option 2: Manual GitHub Pages Setup

1. Go to your repository Settings → Pages
2. Set Source to "Deploy from a branch"
3. Select branch: `main` (or `gh-pages`)
4. Select folder: `/docs`
5. Click Save

GitHub Pages will automatically build and serve the site from the `docs/` directory.

### Option 3: Deploy from `gh-pages` Branch

If you prefer to deploy from a separate branch:

```bash
# Build the site
bundle exec jekyll build

# Copy _site contents to gh-pages branch
# (GitHub Pages will serve from the root of gh-pages branch)
```

## Local Development

For local development that matches GitHub Pages:

```bash
cd docs
bundle install
bundle exec jekyll serve --baseurl /serger
```

The documentation will be available at `http://localhost:4000/serger/`

Note: The `github-pages` gem ensures your local environment matches GitHub Pages exactly.

