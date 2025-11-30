package servlets;

import java.io.FileNotFoundException;
import java.io.IOException;
import java.util.Iterator;
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

@WebServlet("/api/schedule/remove")
public class ScheduleApiRemove extends HttpServlet {
    private static final long serialVersionUID = 1L;

    public ScheduleApiRemove() throws FileNotFoundException, IOException {
    }

    @Override
    protected void doPost(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        JsonObject body = readBody(request);
        String uuid = getString(body, request, "uuid");

        if (uuid == null) {
            response.sendError(HttpServletResponse.SC_BAD_REQUEST, "Missing uuid");
            return;
        }

        List<ScheduleEntry> schedule = DataProvider.getSchedule();

        Iterator<ScheduleEntry> iterator = schedule.iterator();
        while (iterator.hasNext()) {
            ScheduleEntry entry = iterator.next();
            if (uuid.equals(entry.uuid)) {
                iterator.remove();
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
}
