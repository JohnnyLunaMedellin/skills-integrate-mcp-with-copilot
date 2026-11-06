document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const loginForm = document.getElementById("login-form");
  const logoutButton = document.getElementById("logout-button");
  const signupTitle = document.getElementById("signup-title");
  const authStatus = document.getElementById("auth-status");
  const messageDiv = document.getElementById("message");
  let isAdmin = false;

  function showMessage(message, type) {
    messageDiv.textContent = message;
    messageDiv.className = type;
    messageDiv.classList.remove("hidden");
    setTimeout(() => messageDiv.classList.add("hidden"), 5000);
  }

  function renderAuthState() {
    loginForm.classList.toggle("hidden", isAdmin);
    logoutButton.classList.toggle("hidden", !isAdmin);
    signupForm.classList.toggle("hidden", !isAdmin);
    signupTitle.textContent = isAdmin ? "Register a Student" : "Staff Sign In";
    authStatus.textContent = isAdmin
      ? "Signed in as staff. You can register or unregister students."
      : "Staff sign-in is required to manage student registrations.";
  }

  function addText(parent, tagName, text, className = "") {
    const element = document.createElement(tagName);
    element.textContent = text;
    if (className) element.className = className;
    parent.appendChild(element);
    return element;
  }

  function renderActivity(name, details) {
    const activityCard = document.createElement("div");
    activityCard.className = "activity-card";
    addText(activityCard, "h4", name);
    addText(activityCard, "p", details.description);
    addText(activityCard, "p", `Schedule: ${details.schedule}`);

    const spotsLeft = details.max_participants - details.participants.length;
    addText(activityCard, "p", `Availability: ${spotsLeft} spots left`);

    const participantsContainer = document.createElement("div");
    participantsContainer.className = "participants-container";
    if (details.participants.length > 0) {
      const participantsSection = document.createElement("div");
      participantsSection.className = "participants-section";
      addText(participantsSection, "h5", "Participants:");
      const participantsList = document.createElement("ul");
      participantsList.className = "participants-list";

      details.participants.forEach((email) => {
        const participant = document.createElement("li");
        addText(participant, "span", email, "participant-email");

        if (isAdmin) {
          const deleteButton = document.createElement("button");
          deleteButton.className = "delete-btn";
          deleteButton.type = "button";
          deleteButton.textContent = "❌";
          deleteButton.setAttribute("aria-label", `Unregister ${email}`);
          deleteButton.dataset.activity = name;
          deleteButton.dataset.email = email;
          participant.appendChild(deleteButton);
        }

        participantsList.appendChild(participant);
      });

      participantsSection.appendChild(participantsList);
      participantsContainer.appendChild(participantsSection);
    } else {
      addText(participantsContainer, "p", "No participants yet");
    }

    activityCard.appendChild(participantsContainer);
    activitiesList.appendChild(activityCard);
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) throw new Error("Failed to load activities");
      const activities = await response.json();

      activitiesList.replaceChildren();
      activitySelect.replaceChildren(new Option("-- Select an activity --", ""));
      Object.entries(activities).forEach(([name, details]) => {
        renderActivity(name, details);
        activitySelect.add(new Option(name, name));
      });
    } catch (error) {
      activitiesList.textContent = "Failed to load activities. Please try again later.";
      console.error("Error fetching activities:", error);
    }
  }

  async function handleUnregister(button) {
    const activity = button.dataset.activity;
    const email = button.dataset.email;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/unregister?email=${encodeURIComponent(email)}`,
        { method: "DELETE" },
      );
      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        await fetchActivities();
      } else {
        if (response.status === 401) {
          isAdmin = false;
          renderAuthState();
          await fetchActivities();
        }
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to unregister. Please try again.", "error");
      console.error("Error unregistering:", error);
    }
  }

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const result = await response.json();
      if (!response.ok) {
        showMessage(result.detail || "Staff sign-in failed.", "error");
        return;
      }

      isAdmin = true;
      loginForm.reset();
      renderAuthState();
      showMessage(result.message, "success");
      await fetchActivities();
    } catch (error) {
      showMessage("Unable to sign in. Please try again.", "error");
      console.error("Error signing in:", error);
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/auth/logout", { method: "POST" });
      const result = await response.json();
      if (!response.ok) {
        showMessage(result.detail || "Failed to sign out.", "error");
        return;
      }

      isAdmin = false;
      renderAuthState();
      await fetchActivities();
      showMessage(result.message, "success");
    } catch (error) {
      showMessage("Unable to sign out. Please try again.", "error");
      console.error("Error signing out:", error);
    }
  });

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = activitySelect.value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/signup?email=${encodeURIComponent(email)}`,
        { method: "POST" },
      );
      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        signupForm.reset();
        await fetchActivities();
      } else {
        if (response.status === 401) {
          isAdmin = false;
          renderAuthState();
          await fetchActivities();
        }
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to sign up. Please try again.", "error");
      console.error("Error signing up:", error);
    }
  });

  activitiesList.addEventListener("click", (event) => {
    const button = event.target.closest(".delete-btn");
    if (button && isAdmin) handleUnregister(button);
  });

  async function initialize() {
    renderAuthState();
    try {
      const response = await fetch("/auth/session");
      if (!response.ok) {
        const result = await response.json();
        throw new Error(result.detail || "Unable to check staff session.");
      }
      const session = await response.json();
      isAdmin = session.authenticated;
    } catch (error) {
      showMessage(error.message, "error");
      console.error("Error checking staff session:", error);
    }
    renderAuthState();
    await fetchActivities();
  }

  initialize();
});
