/*
 * Main application logic for Photo Search and Upload
 */

document.addEventListener("DOMContentLoaded", function () {
  // Initialize API client
  const apigClient = apigClientFactory.newClient();

  // Set up event listeners
  document
    .getElementById("searchButton")
    .addEventListener("click", performSearch);
  document
    .getElementById("uploadButton")
    .addEventListener("click", uploadPhoto);

  // Search photos function
  function performSearch() {
    const query = document.getElementById("searchQuery").value.trim();
    if (!query) {
      alert("Please enter a search term");
      return;
    }

    // Show loading state
    const resultsDiv = document.getElementById("searchResults");
    resultsDiv.innerHTML = "<p>Loading results...</p>";

    // Call API
    const params = {
      q: query,
    };

    apigClient
      .searchGet(params, {}, {})
      .then(function (result) {
        displaySearchResults(result["data"]["results"]);
      })
      .catch(function (error) {
        console.error("Error performing search:", error);
        resultsDiv.innerHTML =
          "<p>Error performing search. Please try again.</p>";
      });
  }

  // Display search results
  function displaySearchResults(results) {
    const resultsDiv = document.getElementById("searchResults");
    resultsDiv.innerHTML = "";

    if (!results || !results.length) {
      resultsDiv.innerHTML = "<p>No results found.</p>";
      return;
    }

    results.forEach((photo) => {
      const photoCard = document.createElement("div");
      photoCard.className = "photo-card";

      // Create image element
      const img = document.createElement("img");
      img.src = photo.url; // Assuming the API returns a URL for each photo
      img.alt = "Photo result";

      // Create labels section
      const labelsDiv = document.createElement("div");
      labelsDiv.className = "photo-labels";

      // Add label chips
      const labelsChips = document.createElement("div");
      labelsChips.className = "label-chips";

      if (photo.labels && photo.labels.length) {
        photo.labels.forEach((label) => {
          const chip = document.createElement("span");
          chip.className = "label-chip";
          chip.textContent = label;
          labelsChips.appendChild(chip);
        });
      } else {
        const noLabels = document.createElement("span");
        noLabels.textContent = "No labels";
        labelsChips.appendChild(noLabels);
      }

      // Assemble the card
      labelsDiv.appendChild(labelsChips);
      photoCard.appendChild(img);
      photoCard.appendChild(labelsDiv);
      resultsDiv.appendChild(photoCard);
    });
  }

  // Upload photo function
  function uploadPhoto() {
    const fileInput = document.getElementById("photoUpload");
    const label1 = document.getElementById("label1").value.trim();
    const label2 = document.getElementById("label2").value.trim();

    // Validate input
    if (!fileInput.files || fileInput.files.length === 0) {
      showStatus("Please select a file to upload", "error");
      return;
    }

    const file = fileInput.files[0];

    // Prepare custom labels
    let customLabels = "";
    if (label1) {
      customLabels = label1;
      if (label2) {
        customLabels += `,${label2}`;
      }
    } else if (label2) {
      customLabels = label2;
    }

    const s3UploadUrl = `https://my-photo-bucket20250427.s3.us-east-2.amazonaws.com/${encodeURIComponent(
      file.name
    )}`;

    const headers = {
      "Content-Type": file.type,
      "x-amz-meta-customLabels": customLabels,
    };

    // Show loading state
    showStatus("Uploading photo...", "info");

    axios
      .put(s3UploadUrl, file, { headers })
      .then(function (response) {
        console.log("Upload success:", response);
        showStatus("Photo uploaded successfully!", "success");

        // Clear form
        fileInput.value = "";
        document.getElementById("label1").value = "";
        document.getElementById("label2").value = "";
      })
      .catch(function (error) {
        console.error("Upload failed:", error);
        showStatus("Error uploading photo. Please try again.", "error");
      });
  }

  // Helper function to show status messages
  function showStatus(message, type) {
    const statusMessage = document.getElementById("statusMessage");
    statusMessage.textContent = message;
    statusMessage.className = type;
    statusMessage.classList.remove("hidden");

    // Automatically hide success messages after 5 seconds
    if (type === "success") {
      setTimeout(() => {
        statusMessage.classList.add("hidden");
      }, 5000);
    }
  }
});
