#!/bin/bash
# Test Runner Script for Georgian Voiceover App

set -e  # Exit on error

echo "====================================="
echo "Georgian Voiceover App - Test Runner"
echo "====================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    print_error "pytest not found. Installing dependencies..."
    pip install -r requirements-dev.txt
fi

# Parse arguments
MODE=${1:-"all"}

case $MODE in
    "all")
        print_status "Running all tests..."
        pytest -v
        ;;
    "unit")
        print_status "Running unit tests only..."
        pytest -m unit -v
        ;;
    "integration")
        print_status "Running integration tests only..."
        pytest -m integration -v
        ;;
    "coverage")
        print_status "Running tests with coverage report..."
        pytest --cov=src --cov=app --cov-report=html --cov-report=term-missing
        print_status "Coverage report generated: htmlcov/index.html"
        ;;
    "fast")
        print_status "Running tests in parallel..."
        pytest -n auto -v
        ;;
    "smoke")
        print_status "Running smoke tests..."
        pytest -m smoke -v
        ;;
    "watch")
        print_status "Running tests in watch mode..."
        pytest-watch
        ;;
    *)
        print_warning "Unknown mode: $MODE"
        echo ""
        echo "Usage: ./run_tests.sh [mode]"
        echo ""
        echo "Modes:"
        echo "  all         - Run all tests (default)"
        echo "  unit        - Run unit tests only"
        echo "  integration - Run integration tests only"
        echo "  coverage    - Run with coverage report"
        echo "  fast        - Run in parallel (faster)"
        echo "  smoke       - Run smoke tests only"
        echo "  watch       - Run in watch mode"
        exit 1
        ;;
esac

# Exit with pytest's exit code
exit $?
