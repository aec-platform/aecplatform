.PHONY: help build serve test check check-packages org-readme clean

PORT ?= 8492

help:
	@echo "make build       generate site/ from registry/products.json"
	@echo "make serve       build, then serve site/ on http://localhost:$(PORT)"
	@echo "make test        run the test suite"
	@echo "make check       validate the registry without writing anything"
	@echo "make org-readme  print the GitHub org profile README"
	@echo "make clean       remove site/"

build:
	python3 -m build.site

serve: build
	@echo "http://localhost:$(PORT)"
	@python3 -m http.server $(PORT) --directory site

test:
	python3 -m pytest -q

# Exits non-zero and lists every problem, so it works as a pre-commit gate.
check:
	@python3 -c "from build.site import Registry; p=Registry.load().validate(); \
	print('\n'.join(p) or 'registry ok'); raise SystemExit(1 if p else 0)"

# Needs network, so it is deliberately not part of `make check`.
check-packages:
	@python3 -m build.check_packages

org-readme:
	@python3 -m build.org_readme

clean:
	rm -rf site
