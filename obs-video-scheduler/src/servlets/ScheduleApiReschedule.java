package servlets;

import java.io.FileNotFoundException;
import java.io.IOException;
import java.util.List;

import javax.json.Json;
import javax.json.JsonObject;
import javax.json.JsonReader;
import javax.servlet.ServletException;
import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import util.DataProvider;
import util.ScheduleEntry;

@WebServlet("/api/schedule/reschedule")
public class ScheduleApiReschedule extends HttpServlet {
    private static final long serialVersionUID = 1L;

    public ScheduleApiReschedule() throws FileNotFoundException, IOException {
    }

    @Override
    protected void doPost(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        JsonObject body = readBody(request);
        String uuid = getString(body, request, "uuid");
        Long start = getLong(body, request, "start");

        if (uuid == null || start == null) {
            response.sendError(HttpServletResponse.SC_BAD_REQUEST, "Missing uuid or start");
            return;
        }

        List<ScheduleEntry> schedule = DataProvider.getSchedule();

        for (ScheduleEntry entry : schedule) {
            if (uuid.equals(entry.uuid)) {
                entry.start = start;
                break;
            }
        }

        DataProvider.updateSchedule(schedule);

        DataProvider.writeScheduleToClient(response);
    }

    private JsonObject readBody(HttpServletRequest request) throws IOException {
        try (JsonReader reader = Json.createReader(request.getInputStream())) {
            return reader.readObject();
        } catch (Exception e) {
            return Json.createObjectBuilder().build();
        }
    }

    private String getString(JsonObject body, HttpServletRequest request, String key) {
        if (body.containsKey(key)) {
            return body.getString(key, null);
        }
        return request.getParameter(key);
    }

    private Long getLong(JsonObject body, HttpServletRequest request, String key) {
        try {
            if (body.containsKey(key)) {
                return body.getJsonNumber(key).longValue();
            }
        } catch (Exception ignored) {
        }

        String parameter = request.getParameter(key);
        if (parameter == null) {
            return null;
        }

        try {
            return Long.parseLong(parameter);
        } catch (NumberFormatException e) {
            return null;
        }
    }
}
