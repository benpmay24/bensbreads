document.addEventListener("DOMContentLoaded", function () {
    const links = document.querySelectorAll(".nav-link");
    const currentUrl = window.location.pathname;
  
    links.forEach((link) => {
      if (link.getAttribute("href") === currentUrl) {
        link.classList.add("active");
      }
    });

    // Review form handling
    if (document.getElementById('review-form')) {
        initReviewForm();
    }
});

// Review form functionality
function initReviewForm() {
    // Get all form steps
    const stepSearch = document.getElementById('step-search');
    const stepPlaceInfo = document.getElementById('step-place-info');
    const reviewForm = document.getElementById('review-form');
    
    // Place search functionality
    const placeSearchInput = document.getElementById('place-search');
    const placeSearchResults = document.getElementById('place-search-results');
    const loadingIndicator = document.getElementById('loading-indicator');
    
    // Hidden fields
    const placeIdField = document.getElementById('place_id');
    const placeNameField = document.getElementById('place_name_field');
    const locationField = document.getElementById('location_field');
    
    // Set initial state - only search step is visible
    stepSearch.classList.add('active');
    stepPlaceInfo.classList.remove('active');
    reviewForm.classList.remove('active');
    
    // Handle place search
    if (placeSearchInput) {
        placeSearchInput.addEventListener('input', debounce(function() {
            const query = placeSearchInput.value.trim();
            
            if (query.length < 3) {
                placeSearchResults.innerHTML = '';
                placeSearchResults.style.display = 'none';
                return;
            }
            
            // Show loading indicator
            loadingIndicator.style.display = 'block';
            
            // Call the backend to search for places
            fetch(`/place_search?query=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    loadingIndicator.style.display = 'none';
                    
                    if (data.error) {
                        console.error(data.error);
                        return;
                    }
                    
                    // Display results
                    displayPlaceResults(data.results);
                })
                .catch(error => {
                    console.error('Error searching places:', error);
                    loadingIndicator.style.display = 'none';
                });
        }, 500));
        
        // Function to display place search results
        function displayPlaceResults(results) {
            placeSearchResults.innerHTML = '';
            
            if (!results || results.length === 0) {
                placeSearchResults.innerHTML = '<div class="no-results">No places found</div>';
                placeSearchResults.style.display = 'block';
                return;
            }
            
            results.forEach(place => {
                const placeElement = document.createElement('div');
                placeElement.className = 'place-result';
                placeElement.innerHTML = `
                    <div class="place-name">${place.name}</div>
                    <div class="place-address">${place.formatted_address || place.short_address || 'No address available'}</div>
                    <div class="place-details">
                        ${place.primary_type_display ? `<span class="place-category">${place.primary_type_display}</span>` : ''}
                        ${place.rating ? `<span class="place-rating"><i class="fas fa-star"></i> ${place.rating}</span>` : ''}
                    </div>
                `;
                
                // Add click event to select this place
                placeElement.addEventListener('click', function() {
                    selectPlace(place);
                });
                
                placeSearchResults.appendChild(placeElement);
            });
            
            placeSearchResults.style.display = 'block';
        }
        
        // Function to select a place
        function selectPlace(place) {
            // Hide search results
            placeSearchResults.style.display = 'none';
            
            // Set the hidden field values
            placeIdField.value = place.place_id;
            placeNameField.value = place.name;
            locationField.value = place.formatted_address || place.short_address || '';
            
            // Display selected place info
            document.getElementById('selected-place-name').textContent = place.name;
            
            // Address
            document.getElementById('selected-place-address').textContent = place.formatted_address || place.short_address || 'No address available';
            
            // Rating
            const ratingDisplay = document.getElementById('selected-place-rating');
            if (place.rating) {
                ratingDisplay.innerHTML = '';
                for (let i = 1; i <= 5; i++) {
                    const star = document.createElement('i');
                    star.className = i <= place.rating ? 'fas fa-star' : 'far fa-star';
                    ratingDisplay.appendChild(star);
                }
                ratingDisplay.innerHTML += ` <span>(${place.user_ratings_total || 0} reviews)</span>`;
            } else {
                ratingDisplay.innerHTML = 'No ratings';
            }
            
            // Website
            const websiteContainer = document.getElementById('selected-place-website-container');
            const websiteLink = document.getElementById('selected-place-website');
            if (place.website) {
                websiteLink.href = place.website;
                websiteLink.textContent = place.website.replace(/^https?:\/\//, '').replace(/\/$/, '');
                websiteContainer.style.display = 'flex';
            } else {
                websiteContainer.style.display = 'none';
            }
            
            // Phone
            const phoneContainer = document.getElementById('selected-place-phone-container');
            const phoneSpan = document.getElementById('selected-place-phone');
            if (place.phone_number) {
                phoneSpan.textContent = place.phone_number;
                phoneContainer.style.display = 'flex';
            } else {
                phoneContainer.style.display = 'none';
            }
            
            // Types/tags
            const typesContainer = document.getElementById('selected-place-types');
            typesContainer.innerHTML = '';
            if (place.types && place.types.length) {
                // Display first 3 types as tags
                place.types.slice(0, 3).forEach(type => {
                    const typeSpan = document.createElement('span');
                    typeSpan.className = 'place-tag';
                    typeSpan.textContent = type.replace(/_/g, ' ');
                    typesContainer.appendChild(typeSpan);
                });
            } else {
                typesContainer.innerHTML = 'No categories available';
            }
            
            // Photo
            const photoContainer = document.getElementById('selected-place-photo');
            if (place.photo_url) {
                photoContainer.src = place.photo_url;
            } else {
                photoContainer.src = 'https://via.placeholder.com/400x200?text=No+Image+Available';
            }
            
            // Move to the next step
            stepSearch.classList.remove('active');
            stepPlaceInfo.classList.add('active');
            reviewForm.classList.add('active');
        }
    }
    
    // Star rating functionality
    const starContainers = document.querySelectorAll('.star-container');
    starContainers.forEach(star => {
        star.addEventListener('mouseenter', function() {
            const rating = parseInt(this.dataset.rating);
            const category = this.dataset.category;
            
            // Highlight stars up to the hovered one
            document.querySelectorAll(`.star-container[data-category="${category}"]`).forEach(s => {
                const starRating = parseInt(s.dataset.rating);
                if (starRating <= rating) {
                    s.classList.add('hover');
                } else {
                    s.classList.remove('hover');
                }
            });
        });
        
        star.addEventListener('mouseleave', function() {
            const category = this.dataset.category;
            document.querySelectorAll(`.star-container[data-category="${category}"]`).forEach(s => {
                s.classList.remove('hover');
            });
        });
        
        star.addEventListener('click', function() {
            const rating = parseInt(this.dataset.rating);
            const category = this.dataset.category;
            
            // Set the hidden input value
            document.getElementById(`${category}_input`).value = rating;
            
            // Update the visual state
            document.querySelectorAll(`.star-container[data-category="${category}"]`).forEach(s => {
                const starRating = parseInt(s.dataset.rating);
                if (starRating <= rating) {
                    s.classList.add('active');
                } else {
                    s.classList.remove('active');
                }
            });
            
            // Update overall rating
            updateOverallRating();
        });
    });
    
    // Set initial active state for stars based on hidden input values
    function initializeStarRatings() {
        const ratingCategories = ['food_rating', 'ambience_rating', 'value_rating'];
        
        ratingCategories.forEach(category => {
            const value = parseInt(document.getElementById(`${category}_input`).value) || 0;
            
            document.querySelectorAll(`.star-container[data-category="${category}"]`).forEach(star => {
                const starRating = parseInt(star.dataset.rating);
                if (starRating <= value) {
                    star.classList.add('active');
                } else {
                    star.classList.remove('active');
                }
            });
        });
        
        // Initial overall rating calculation
        updateOverallRating();
    }
    
    // Calculate and update overall rating
    function updateOverallRating() {
        const foodRating = parseInt(document.getElementById('food_rating_input').value) || 0;
        const ambienceRating = parseInt(document.getElementById('ambience_rating_input').value) || 0;
        const valueRating = parseInt(document.getElementById('value_rating_input').value) || 0;
        
        // Simple average calculation
        let overallRating = 0;
        let count = 0;
        
        if (foodRating > 0) {
            overallRating += foodRating;
            count++;
        }
        
        if (ambienceRating > 0) {
            overallRating += ambienceRating;
            count++;
        }
        
        if (valueRating > 0) {
            overallRating += valueRating;
            count++;
        }
        
        const average = count > 0 ? overallRating / count : 0;
        const roundedAverage = Math.round(average * 10) / 10; // Round to 1 decimal place
        
        // Update visual stars
        const stars = document.querySelectorAll('#overall-stars i');
        stars.forEach((star, index) => {
            if (index + 1 <= Math.floor(roundedAverage)) {
                star.className = 'fas fa-star active';
            } else if (index + 1 === Math.ceil(roundedAverage) && roundedAverage % 1 > 0) {
                star.className = 'fas fa-star-half-alt active';
            } else {
                star.className = 'far fa-star';
            }
        });
        
        // Update text value
        document.getElementById('overall-value').textContent = roundedAverage.toFixed(1);
    }
    
    // Initialize star ratings
    initializeStarRatings();
    
    // Form submission handling
    const reviewFormElement = document.getElementById('review-form');
    if (reviewFormElement) {
        reviewFormElement.addEventListener('submit', function(e) {
            // Check if place_id is set
            if (!placeIdField.value) {
                e.preventDefault();
                alert('Please select a place to review first');
                stepSearch.classList.add('active');
                stepPlaceInfo.classList.remove('active');
                reviewForm.classList.remove('active');
                return false;
            }
            
            // Form is valid, proceed with submission
            return true;
        });
    }
}

// Utility function for debouncing input events
function debounce(func, delay) {
    let timeout;
    return function() {
        const context = this;
        const args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), delay);
    };
}