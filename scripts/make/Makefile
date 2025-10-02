.PHONY: help install clean pipeline normalize images sqlite embed index manifests prices publish

help:
	@echo "CardFlux Pipeline Commands"
	@echo ""
	@echo "  make install      - Install all dependencies"
	@echo "  make clean        - Clean all generated artifacts"
	@echo "  make pipeline     - Run full pipeline"
	@echo "  make normalize    - Fetch and normalize card data"
	@echo "  make images       - Download card images"
	@echo "  make sqlite       - Build SQLite database"
	@echo "  make embed        - Generate embeddings"
	@echo "  make index        - Build FAISS indices"
	@echo "  make manifests    - Generate manifests"
	@echo "  make prices       - Fetch price data"
	@echo "  make publish      - Publish to S3/CDN"

install:
	pnpm install
	cd services/embedder && pip install -r requirements.txt
	cd services/indexer && pip install -r requirements.txt

clean:
	rm -rf data/raw/*
	rm -rf data/curated/*
	rm -rf data/images/*
	rm -rf artifacts/metadata/*
	rm -rf artifacts/faiss/*
	rm -rf artifacts/manifests/*
	rm -rf artifacts/price-patches/*

normalize:
	cd services/ingest && pnpm normalize

images:
	cd services/ingest && pnpm fetch-images

sqlite:
	cd services/ingest && pnpm build-sqlite

embed:
	cd services/embedder && pnpm embed

index:
	cd services/indexer && pnpm build-index

manifests:
	cd services/publisher && pnpm generate-manifests

prices:
	cd services/pricefeed && pnpm build-patch

pipeline: normalize images sqlite embed index manifests prices
	@echo "Pipeline complete!"

publish:
	@echo "Publishing artifacts..."
	@echo "TODO: Implement S3 sync"
